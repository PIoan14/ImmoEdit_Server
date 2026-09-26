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
from nano_banana import chat_with_banana
import time
import io
import zipfile
from fastapi.responses import StreamingResponse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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


def get_user_details_by_id(doc_id):
    try:
        doc_ref = db.collection("transactions").document(doc_id)
        doc = doc_ref.get()
        return doc.to_dict()
    except:
        print("No such user found")
    pass


####

def send_email_to_client(email: str, subject: str, body: str) -> None:
    sender_email =  os.getenv("sender_email")
    sender_password = os.getenv("sender_password")
    original_password = os.getenv("original_password")  # Parola de aplicație (App Password)

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, message.as_string())
            print(f"Email trimis cu succes către {email}")
            
    except Exception as e:
        print(f"Eroare la trimiterea emailului: {e}")



def update_twin(doc_id, which_picture, value):

    try:

        print(f"Twinn {doc_id}")
        print(which_picture)
        print(value)
        doc_ref = db.collection("transactions").document(doc_id)
        doc = doc_ref.get()

        print(doc_ref)
        pictures_found = doc.to_dict()["pictures"]
        print(doc.to_dict())

        new_pictures = []
        for picture in pictures_found:

            if picture["picture_content"] == which_picture: 

                print("Picture")
                print(picture)

                picture['twin_content'] = value

            new_pictures.append(picture)
                
        
        doc_ref.update({"pictures": new_pictures})

        return 

    except Exception as e:
        print(e)
        return {"status": 500, "message": str(e)}   


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

def talk_to_banana(nest, path, content_type, transaction_id, transaction_date):

    print("Am început procesarea pe fundal...")

    print(f"Transaction : {transaction_id}, {transaction_date}")
    

    with open(path, "w", encoding="utf-8") as f:
        f.write(nest.model_dump_json(indent=4))

    print("S a scris in json")

    #AI talking

    for picture in nest.pictures:

        out_id =  uuid.uuid4()

        out_file = f"{out_id}.jpg"

        if picture.task == "nature":

            RECEIVED_PICTURES_NATURE = "nature"
            os.makedirs(RECEIVED_PICTURES_NATURE, exist_ok=True)
            for_bucket = os.path.join(RECEIVED_PICTURES_NATURE, out_file)
    
            chat_with_banana(f"./received_pictures/{picture.picture_content}", 
            "Make this code here to look like is being in vs Code dark mode" , 
            f"./nature/{out_file}")

            print("Pushed to Nature")

            upload_to_bucket(for_bucket, blob_name=None, content_type=content_type)

            update_twin(transaction_id, picture.picture_content, out_file)

        else:

            RECEIVED_PICTURES_GEOMETRY = "geometry"
            os.makedirs(RECEIVED_PICTURES_GEOMETRY, exist_ok=True)
            for_bucket = os.path.join(RECEIVED_PICTURES_GEOMETRY, out_file)

            chat_with_banana(f"./received_pictures/{picture.picture_content}", 
            "Make this code here to look like is being in vs Code dark mode" , 
            f"./geometry/{out_file}")

            print("Pushed to Geometry")

            upload_to_bucket(for_bucket , blob_name=None, content_type=content_type)
            
            update_twin(transaction_id, picture.picture_content, out_file)
        
    send_email_to_client(nest.email, f"Batch of pictures ready. Your code {transaction_id}", "")
    


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

    return destination_path

# Testing AREA 

# @app.get("/getProducts")
# def getProducts(email: str):

#     return FileResponse("image.png", media_type="image/png")

@app.get("/getProducts")
def get_products(code: str):

    print(code)

    transaction_details = get_user_details_by_id(code.strip())

    image_paths = []

    for picture in transaction_details["pictures"]:

        image_downloaded = download_from_bucket(picture["twin_content"])

        image_paths.append(image_downloaded)

    
    # Creăm arhiva ZIP în memorie (RAM)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for path in image_paths:
            zip_file.write(path, arcname=path)
            
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=products.zip"}
    )


@app.post("/ReceiveNest")
def receive_nest(nest: Nest, background_tasks: BackgroundTasks):

    # good_format_date = datetime.combine(nest.date, datetime.min.time())

    # nest.date = good_format_date
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
            print(picture.picture_content)
            print("Sleeping")
            time.sleep(2)


        except Exception as e:
            # 1. Salvează detaliile erorii în loguri pentru debugging (recomandat)
            print(f"Eroare la procesarea cererii: {e}")
            
            # 2. Trimite clientului un răspuns de eroare HTTP 500 (Internal Server Error)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A apărut o eroare internă la procesarea datelor."
                # Sau detail=str(e) dacă vrei să trimiți mesajul exact al excepției către client
            )
        
    
    update_time, doc_ref = db.collection("transactions").add(nest.model_dump())
    background_tasks.add_task(talk_to_banana, nest, "nest.json", content_type, doc_ref.id ,update_time)

    return {"status": "success", "message": "Cererea a fost primită și se procesează."}
          # Salvarea în fișier
        


# @app.post("/ReceiveNest")
# def receive_nest(email: str):

#     #Get user 
#     download_from_bucket()
#     pass

if __name__ == "__main__":
    # upload_to_bucket("image.png")
    # download_from_bucket()
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)