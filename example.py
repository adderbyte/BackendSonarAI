import os

import openai
from typing import Annotated
import time
from yival.logger.token_logger import TokenLogger
from yival.schemas.experiment_config import MultimodalOutput
from yival.states.experiment_state import ExperimentState
from yival.wrappers.string_wrapper import StringWrapper

import ray
from datasets import Audio, Dataset
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from ray import serve

## for loading file
from langchain.document_loaders import PyPDFLoader
from unstructured.partition.auto import partition

import inspect
# from langchain.document_loaders import unstructuredLoader
import requests
from dotenv import load_dotenv




# 1: Define a FastAPI app and wrap it in a deployment with a route handler.
app = FastAPI()

 ## application root
@app.get("/")
def root(self):

    ### get env key for unstrcutured data set
    ### change to os.getenv later
    undstructured_loader_key = os.environ["UNSTRUCTURED_API_KEY"]

        # Ensure you have your OpenAI API key set up
    openai.api_key = os.getenv("OPENAI_API_KEY")

    return JSONResponse(
            content={"message": " Summmarizing Documents..."}, status_code=200
        )


@serve.deployment(
    autoscaling_config={"min_replicas": 1, "max_replicas": 1},
    ray_actor_options={"num_cpus": 1}
)
@serve.ingress(app)
class Summarizer:
    def __init__(self):
        '''

        no need to initialize instance variales
        '''
        # self._processor = AutoFeatureExtractor.from_pretrained(model)
        # self._model = Wav2Vec2ForSequenceClassification.from_pretrained(model)
        # self._podcast_length = None
        # self._expertise_level =  None
        # self._msg =  message
        # self._count =  count
        print("========================here")


    def is_pdf(self,file_path): 
        """
        check if file path ends in .pdf
        """
        return file_path.lower().endswith('.pdf')

    def get_response(self, file_uploaded, filename):
        """
        Load docuemnts
        check if pdf else it is unstrcuted tupe ---> use the UnstrcutedLoaderAPI

        LangChain can load from URL but install libMagic first: 
        https://github.com/langchain-ai/langchain/issues/5342
        """
        if self.is_pdf(filename):
            # load file
            loader_pdf = PyPDFLoader(file_uploaded)
            article_dataset = loader_pdf.load() 
        else:
            loader_pdf = partition(data_file_path) #UnstructuredLoader(data_file_path)
            article_dataset =   "\n".join([str(el) for el in loader_pdf])                             # loader_pdf.load()
    
        return article_dataset

    def articleSummarizer(self,article: str, state: ExperimentState, podcast_length:int, expertise_level:str) -> MultimodalOutput:

        ### temp_file loator
        # Save the audio file to a temporary location

        # temp_file_path = f"temp/{datafile.filename}"
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
                       Weave the document content into a cohesive narrative appropriate for the  podcast length of {podcast_length} minutes.   \
                       Use language and concepts suitable for an audience with {expertise_level} expertise \
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
            "content": article
        }]
        # Use the chat-based completion
        response = openai.ChatCompletion.create(model="gpt-4", messages=messages)

        answer = MultimodalOutput(
            text_output=response['choices'][0]['message']['content'],
        )
        token_usage = response['usage']['total_tokens']
        logger.log(token_usage)

        return answer

   
    @app.post("/submitform/")
    async def doSummary(self, 
        datafile:Annotated[UploadFile, File(...)],# UploadFile=File(...),# datafiles: UploadFile = File(...), 
        podcast_length: Annotated[int, Form()],# podcast_length: int=Form(),
        expertise_level: Annotated[str,Form()], 
        link_name: Annotated[str, Form()] # link_name: str= Form()
        ):

         temp_file_path = None

         ### get file name 
         ### first, check if link to file was provided 
         if not link_name.strip() : ### check if link field is empty 
            #### save file for later loading to pdf
            temp_file_path = f"/tmp/{datafile.filename}" 
            with open(temp_file_path, "wb") as file: 
                content = await datafile.read() 
                file.write(content) 

            # Now use the saved file path with PyPDFLoader 
            article =  self.get_response(temp_file_path,filename=datafile.filename)
         ## if link field is not empty
         else: 
            try: 
               ## check if link responsive
               response = requests.head(link_name, allow_redirects=True) # Use HEAD to avoid downloading the whole page 
               if response.status_code == 200:  ## if link is responsive
                     temp_file_path =  link_name
               else: ## if link is not responsive
                     if datafile is None:  # check if File was not uploaded once link is not responsue
                        return JSONResponse( content={"error": "No file uploaded. and link to file name is not responsive"}, status_code=400 ) # Optional: Check
                     else: ##  get file bame id file was provided
                        fileUploaded= datafile#f"temp/{datafile.filename}"#datafile.filename
            except:

                    return JSONResponse( content={"error": "Inputs are invlaid. Input should be uploaded file or a link to a file"}, status_code=400 )

                    # if the file is empty content = await file.read() if not content: return JSONResponse( content={"error": "Uploaded file is empty."}, status_code=400 ) 

         
        
             

         print( datafile.filename, podcast_length, expertise_level,link_name ,"=============================I am the file ==========================")

         print("------------the data file is now ready --------------", article[0:20])
         # with open(temp_file_path, "wb") as audio_file:
         #    contents = await audio.read()
         #    audio_file.write(contents)

        #  answer = Summarizer.articleSummarizer(article=article, 
        #     podcast_length=podcast_length,expertise_level=expertise_level )

        #  print("=============")
        #  print(answer)

        #  print("===============")

        #  # Return the result
         return JSONResponse(
            content={"voice_model_parameters": [
            {
            "filename":datafile.filename,
             "length":podcast_length,
             "expertise_level":expertise_level,
             "link_name":link_name

             }

             ] 

             }, status_code=200
        )












sonarllm = Summarizer.bind()

serve.run(sonarllm,route_prefix="/")

while True:
    time.sleep(20000)

