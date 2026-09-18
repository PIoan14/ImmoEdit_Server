from fastapi import FastAPI, HTTPException, status, logger, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from models import Nest
import base64
import uuid
from google.cloud import storage
import os
import uvicorn
import mimetypes
import json
import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore
from datetime import datetime, date


load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


firebase_creds_json = os.getenv("FIREBASE_CRED")

if firebase_creds_json:
   
    cred_dict = json.loads(firebase_creds_json)
  
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
else:
    print("EROARE")

db = firestore.client(database_id="immo-edit-fb")

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "immoapp-508512-dd76def4bfdf.json"
gc_storage_client = storage.Client()
# bucket = gc_storage_client.bucket("original_pictures")
# bucket.location = "US"
# bucket = gc_storage_client.create_bucket(bucket)

#db.collection("users").add(user.model_dump())


RECEIVED_PICTURES_DIR = "received_pictures"

def talk_to_banana(nest, path):

    print("Am început procesarea pe fundal...")

    #AI talking

    # ... os.makedirs, upload în bucket, salvare în Firestore etc.
    print("Procesarea s-a terminat cu succes!")
    with open(path, "w", encoding="utf-8") as f:
        f.write(nest.model_dump_json(indent=4))


def upload_to_bucket(local_path, blob_name=None, content_type=None):
    blob_name = blob_name or os.path.basename(local_path)
    
    # Auto-detectează MIME type dacă nu a fost specificat
    if not content_type:
        content_type, _ = mimetypes.guess_type(local_path)
        content_type = content_type or "image/jpeg"

    my_bucket = gc_storage_client.bucket("original_pictures")
    blob = my_bucket.blob(blob_name)
    
    blob.upload_from_filename(local_path, content_type=content_type)



def download_from_bucket(picture_name: str, destination_path: str = None):

    destination_path = destination_path or picture_name

    my_bucket = gc_storage_client.get_bucket("original_pictures")
    
    blob = my_bucket.blob(picture_name)

    with open(destination_path, "wb") as f:
        gc_storage_client.download_blob_to_file(blob, f)

# Testing AREA 

@app.get("/test")
def test():
    return FileResponse("image.png", media_type="image/png")


@app.post("/ReceiveNest")
def receive_nest(nest: Nest, background_tasks: BackgroundTasks):

    good_format_date = datetime.combine(nest.date, datetime.min.time())

    nest.date = good_format_date
    os.makedirs(RECEIVED_PICTURES_DIR, exist_ok=True)

    json_path = os.path.join(RECEIVED_PICTURES_DIR, "nest_data.json")


    for picture in nest.pictures:
        content = picture.picture_content

        content_type = "image/png"
        if "," in content:
            header, content = content.split(",", 1)
            if ":" in header and ";" in header:
                content_type = header.split(":", 1)[1].split(";", 1)[0]

        missing_padding = len(content) % 4
        if missing_padding:
            content += "=" * (4 - missing_padding)

        extension = "jpg" if content_type in ("image/jpeg", "image/jpg") else "png"

        try:
            binary_data = base64.b64decode(content)
            uniqe_picture_id = uuid.uuid4()
            file_name = f"{uniqe_picture_id}.{extension}"
            picture.picture_content = file_name
            local_path = os.path.join(RECEIVED_PICTURES_DIR, file_name)

            with open(local_path, "wb") as f:
                f.write(binary_data)

            upload_to_bucket(local_path, blob_name=file_name, content_type=content_type)

            # Stocare firebase
            db.collection("transactions").add(nest.model_dump())
            background_tasks.add_task(talk_to_banana, nest, "nest.json")

            return {"status": "success", "message": "Cererea a fost primită și se procesează."}

            # Aici ar veni un talk to gemini de local_path --> AI generated local_path content

            # Upload_to_bucket(AI generated local_path content)

            # Update firebase

            # remove both files

        except Exception as e:
            # 1. Salvează detaliile erorii în loguri pentru debugging (recomandat)
            print(f"Eroare la procesarea cererii: {e}")
            
            # 2. Trimite clientului un răspuns de eroare HTTP 500 (Internal Server Error)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A apărut o eroare internă la procesarea datelor."
                # Sau detail=str(e) dacă vrei să trimiți mesajul exact al excepției către client
            )
          # Salvarea în fișier
        


@app.post("/ReceiveNest")
def receive_nest(email: str):

    #Get user 
    download_from_bucket()
    pass

if __name__ == "__main__":
    # upload_to_bucket("image.png")
    # download_from_bucket()
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)