import os

import openai

from yival.logger.token_logger import TokenLogger
from yival.schemas.experiment_config import MultimodalOutput
from yival.states.experiment_state import ExperimentState
from yival.wrappers.string_wrapper import StringWrapper

import ray
from datasets import Audio, Dataset
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from ray import serve

## for loading file
from langchain_community.document_loaders import PyPDFLoader
from langchain_unstructured import UnstructuredLoader




# 1: Define a FastAPI app and wrap it in a deployment with a route handler.
app = FastAPI()



 """
 (1) Handle form data based on the web page
 (2) Use state monitoring to  summary is not called intil get data is called 


 """
## application root
@app.get("/")
def root():

    ### get env key for unstrcutured data set
    ### change to os.getenv later
    undstructured_loader_key = os.environ["UNSTRUCTURED_API_KEY"]

    # Ensure you have your OpenAI API key set up
    openai.api_key = os.getenv("OPENAI_API_KEY")

    return JSONResponse(
        content={"message": " Summmarizing Documents..."}, status_code=200
    )


@serve.ingress(app)
class Summarizer:
    def __init__(self, podcast_length: int, expertise_level: str):
        # self._processor = AutoFeatureExtractor.from_pretrained(model)
        # self._model = Wav2Vec2ForSequenceClassification.from_pretrained(model)
        self._podcast_length = None
        self._expertise_level =  None
        self._UploadDile =  None


     def is_pdf(file_path): 
        """
        check if file path ends in .pdf
        """
        return file_path.lower().endswith('.pdf')

    def get_response(self, data_file_path: str):
        """
        Load docuemnts
        check if pdf else it is unstrcuted tupe ---> use the UnstrcutedLoaderAPI

        LangChain can load from URL but install libMagic first: 
        https://github.com/langchain-ai/langchain/issues/5342
        """
        if is_pdf(data_file_path):
            # load file
            loader_pdf = PyPDFLoader(data_file_path)
            article_dataset = loader_pdf.load() 
        else:
            loader_pdf = UnstructuredLoader(data_file_path)
            docs = loader_pdf.load()
    
        return article_dataset


    ## this handles parameters from the form
    @app.post("/submit/")
    async def login(UploadFile: Annotated[File(...), Form()], podcast_length: Annotated[intr, Form()],
     expertise_level: Annotated[str, Form()]):
         self._podcast_length = podcast_length
         self._expertise_level =  expertise_level
         self._UploadDile =  UploadFile
         
          # return {"username": username, expertise_level,podcast_length }
    
    ## this handles parameters from the form
    @app.post("/submit-json/")
    async def login_json(UploadFile: file = Body(...)  ,podcast_length: str = Body(...), expertise_level: str = Body(...)):
       print("password", password)
       self._podcast_length = podcast_length
       self._expertise_level =  expertise_level
       self._UploadDile =  UploadFile
       #return return {"username": username, expertise_level,podcast_length }

    @app.get("/get_summary")
    def summarize(self,article: str, state: ExperimentState) -> MultimodalOutput:

        ### temp_file loator
        # Save the audio file to a temporary location

        temp_file_path = f"temp/{datafile.filename}"
        ## logging
        logger = TokenLogger()
        logger.reset()
        

        # Create a chat message sequence
        messages = [{
            "role":
            "system",
            "content":
            ### use f string for formatting f" the string + podcast_length + experience_level " ---> this is more expressive
            #### or "the  string {}, string , {}".format(podcast_length, experience_level)
            str(
                StringWrapper(
            f"(1) Task: create an exciting and captivating podcast script based on the provided document content.\
                       Tailor the script for students, presenting the information as a compelling story with a narrative.\
                       Output only the words to be spoken aloud. Do not include any stage directions, sound effects, \
                       structural markers, or non-spoken text.\n \
             (2) Instructions: Begin with a powerful hook or intriguing question to immediately \
                       capture the listener's attention. Avoid too many podcast norms and go right into telling the engaging story.  \
                       Make sure that you acknowledge the source materials and authors by name.   \
                       Weave the document content into a cohesive narrative appropriate for the  podcast length of {self._podcast_length} minutes.   \
                       Use language and concepts suitable for an audience with {self._expertise_level} expertise \
                       Incorporate storytelling elements such as anecdotes, vivid descriptions, and dynamic pacing to maintain engagement. \
                       Conclude with a memorable ending that reinforces the key insights or prompts the audience to reflect further.\n  \
             (3) Guidelines: Engagement: Keep the tone lively and captivating to sustain interest throughout.   \
                        Clarity: Ensure complex ideas are communicated clearly without oversimplification \
                        Respect the Content: Remain faithful to the original document's intent and message.  \
                        Exclusive Spoken Words: Only include text that is meant to be spoken aloud. Avoid any brackets, parentheses, or notes, including things like `Opening` or `Body`. \
                    ",
                    name="summarization",
                    state=state
                )
            )
        }, {
            "role": "user",
            "content": self.get_response(temp_file_path) #article
        }]
        # Use the chat-based completion
        response = openai.ChatCompletion.create(model="gpt-4", messages=messages)

        answer = MultimodalOutput(
            text_output=response['choices'][0]['message']['content'],
        )
        token_usage = response['usage']['total_tokens']
        logger.log(token_usage)

        return answer




ray.init(_node_ip_address="0.0.0.0", ignore_reinit_error=True)

serve.start(
    detached=True,
    http_options={"host": "0.0.0.0", "port": int(os.environ.get("PORT", "8000"))},
)

lid_inference = Summarizer()

serve.run(lid_inference)



