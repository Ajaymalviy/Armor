# -*- coding: utf-8 -*-
"""person reid kaggle.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1aoLU-BhF4UIPdyIqT0IMPEziJ2ZVf7l8
"""

!pip install segmentation-models-pytorch -q
!pip install -U git+https://github.com/albumentations-team/albumentations -q
!pip install --upgrade opencv-contrib-python -q

!git clone https://github.com/parth1620/Person-Re-Id-Dataset

import sys
sys.path.append("/content/Person-Re-Id-Dataset")

!pip install timm

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import torch

"""
Timm: PyTorch Image Models (timm) is a library for state-of-the-art-image classification, containing a collection of image models, optimizers, schedulers, augmentations and much more.
"""
import timm

import torch.nn.functional as F
from torch import nn
from torch.utils.data import Dataset, DataLoader

from skimage import io
from sklearn.model_selection import train_test_split

"""
tqdm is a library that is used for creating Python Progress Bars. It gets its name from the Arabic name taqaddum, which means 'progress. '
"""
from tqdm import tqdm

import zipfile
import os

# Path to the ZIP file
zip_file_path = '/archive.zip'

# Directory where you want to extract the files
extract_to_dir = '/content/'

# Create the directory if it doesn't exist
os.makedirs(extract_to_dir, exist_ok=True)

# Unzip the file
with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
    zip_ref.extractall(extract_to_dir)

DATA_DIR = "/content/Market-1501-v15.09.15/bounding_box_train"
CSV_FILE = "/content/Person-Re-Id-Dataset/train.csv"

BATCH_SIZE = 32
LR = 0.001
EPOCHS = 15

DEVICE = 'cuda'

df = pd.read_csv(CSV_FILE)
df.head()

row = df.iloc[11]



A_img = io.imread(DATA_DIR +"/"+ row.Anchor)
P_img = io.imread(DATA_DIR +"/"+ row.Positive)
N_img = io.imread(DATA_DIR +"/"+ row.Negative)

fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize = (10,5))

ax1.set_title("Anchor")
ax1.imshow(A_img)

ax2.set_title("Positive")
ax2.imshow(P_img)

ax3.set_title("Negative")
ax3.imshow(N_img)
train_df, valid_df = train_test_split(df, test_size = 0.20, random_state = 42)

class APN_Dataset(Dataset):

    def __init__(self, df):
        self.df = df

    def __len__(self):
        return len(self.df)

    def __getitem__(self,idx):
        row = self.df.iloc[idx]

        A_img = io.imread(DATA_DIR +"/"+ row.Anchor)
        P_img = io.imread(DATA_DIR +"/"+ row.Positive)
        N_img = io.imread(DATA_DIR +"/"+ row.Negative)

        A_img = torch.from_numpy(A_img).permute(2, 0 ,1) / 255.0
        P_img = torch.from_numpy(P_img).permute(2, 0 ,1) / 255.0
        N_img = torch.from_numpy(N_img).permute(2, 0 ,1) / 255.0

        return A_img, P_img, N_img

trainset = APN_Dataset(train_df)
validset = APN_Dataset(valid_df)

print(f"Size of trainset : {len(trainset)}")
print(f"Size of validset : {len(validset)}")

idx = 40
A,P,N = trainset[idx]

f, (ax1, ax2, ax3) = plt.subplots(1,3,figsize= (10,5))

ax1.set_title('Anchor')
ax1.imshow(A.numpy().transpose((1,2,0)), cmap = 'gray')

ax2.set_title('Positive')
ax2.imshow(P.numpy().transpose((1,2,0)), cmap = 'gray')

ax3.set_title('Negative')
ax3.imshow(N.numpy().transpose((1,2,0)), cmap = 'gray')



trainloader = DataLoader(trainset, batch_size = BATCH_SIZE,shuffle = True)
validloader = DataLoader(validset, batch_size = BATCH_SIZE)
print(f"No. of batches in trainloader : {len(trainloader)}")
print(f"No. of batches in validloader : {len(validloader)}")
for A, P, N in trainloader:
    break;

print(f"One image batch shape : {A.shape}")

class APN_Model(nn.Module):

    def __init__(self, emb_size = 512):
        super(APN_Model, self).__init__()

        self.efficientnet = timm.create_model('efficientnet_b0', pretrained=True)
        self.efficientnet.classifier = nn.Linear(in_features = self.efficientnet.classifier.in_features,
                                                out_features = emb_size)


    def forward(self, images):
        embeddings = self.efficientnet(images)
        return embeddings
model = APN_Model()
model.to(DEVICE)

def train_fn(model, dataloader, optimizer, criterion):
    model.train() # ON Dropout
    total_loss = 0.0

    for A,P,N in tqdm(dataloader):
        A,P,N = A.to(DEVICE), P.to(DEVICE), N.to(DEVICE)

        A_embs = model(A)
        P_embs = model(P)
        N_embs = model(N)

        loss = criterion(A_embs, P_embs, N_embs)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    return total_loss / len(dataloader)
    def eval_fn(model, dataloader, criterion):
      model.eval()  # OFF Dropout
      total_loss = 0.0

      with torch.no_grad():
          for A,P,N in tqdm(dataloader):
              A,P,N = A.to(DEVICE), P.to(DEVICE), N.to(DEVICE)

              A_embs = model(A)
              P_embs = model(P)
              N_embs = model(N)

              loss = criterion(A_embs, P_embs, N_embs)

              total_loss += loss.item()

          return total_loss / len(dataloader)
criterion = nn.TripletMarginLoss()
optimizer = torch.optim.Adam(model.parameters(), lr = LR)

best_valid_loss = np.Inf

for i in range(EPOCHS):
    train_loss = train_fn(model, trainloader, optimizer, criterion)
    valid_loss = eval_fn(model, validloader, criterion)

    if valid_loss < best_valid_loss:
        torch.save(model.state_dict(), "best_model.pt")
        best_valid_loss = valid_loss
        print("SAVED_WEIGHT_SUCCESS")

    print(f"EPOCHS: {i+1} train_loss: {train_loss} valid_loss: {valid_loss}")

# Check if GPU is available, otherwise use CPU
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
def get_encoding_csv(model, anc_img_names):
    anc_img_names_arr = np.array(anc_img_names)
    encodings = []

    model.eval()
    with torch.no_grad():
        for i in tqdm(anc_img_names_arr):
            A = io.imread(DATA_DIR +"/"+ i)
            A = torch.from_numpy(A).permute(2, 0, 1) / 255.0
            A = A. to(DEVICE)
            A_enc = model(A.unsqueeze(0)) # c,h,w --> (1,c,h,w)
            encodings.append(A_enc.squeeze().cpu().detach().numpy())

        encodings = np.array(encodings)
        encodings = pd.DataFrame(encodings)
        df_enc = pd.concat([anc_img_names, encodings], axis=1)

    return df_enc
model.load_state_dict(torch.load("/best_model.pt"))
df_enc = get_encoding_csv(model, df["Anchor"])
df_enc.to_csv("database.csv", index=False)
df_enc.head()

from google.colab import drive
drive.mount('/content/drive')

def euclidean_dist(img_enc, anc_enc_arr):
    dist = np.sqrt(np.dot(img_enc-anc_enc_arr, (img_enc - anc_enc_arr).T))
    return dist
idx = 0
img_name = df_enc["Anchor"].iloc[idx]
img_path = DATA_DIR +"/"+ img_name

img = io.imread(img_path)
img = torch.from_numpy(img).permute(2, 0, 1) / 255.0

model.eval()
with torch.no_grad():
    img = img.to(DEVICE)
    img_enc = model(img.unsqueeze(0))
    img_enc = img_enc.detach().cpu().numpy()

anc_enc_arr = df_enc.iloc[:, 1:].to_numpy()
anc_img_names = df_enc["Anchor"]
distance = []
print("first:---------",anc_img_names)
print("2:---------",DATA_DIR)
print("3:---------",img)
print("4:---------",img_path)

for i in range(anc_enc_arr.shape[0]):
    dist = euclidean_dist(img_enc, anc_enc_arr[i : i+1, :])
    distance = np.append(distance, dist)
closest_idx = np.argsort(distance)
from utils import plot_closest_imgs
import os
import matplotlib.pyplot as plt
from skimage import io

def plot_closest_imgs(img_names, data_dir, query_img, query_img_path, closest_idx, distances, no_of_closest=10):
    fig, axes = plt.subplots(1, no_of_closest + 1, figsize=(20, 5))  # +1 for query image

    # Query Image
    query_img = io.imread(query_img_path)
    axes[0].imshow(query_img)
    axes[0].set_title('Query Image')
    axes[0].axis('off')

    # Closest Images
    for i in range(min(no_of_closest, len(closest_idx))):  # Ensure not to exceed available images
        img_name = img_names.iloc[closest_idx[i]]
        img_path = os.path.join(data_dir, img_name)  # Correct path joining
        try:
            img = io.imread(img_path)
            axes[i + 1].imshow(img)
            axes[i + 1].set_title(f'Distance: {distances[closest_idx[i]]:.2f}')
            axes[i + 1].axis('off')
        except FileNotFoundError:
            print(f"File not found: {img_path}")
            axes[i + 1].set_title('Not Found')
            axes[i + 1].axis('off')

    plt.tight_layout()
    plt.show()

# Example usage
plot_closest_imgs(anc_img_names, DATA_DIR, img, img_path, closest_idx, distance, no_of_closest=10)

def get_encoding_csv(model, anc_img_names):
    anc_img_names_arr = np.array(anc_img_names)
    encodings = []

    model.eval()
    with torch.no_grad():
        for i in tqdm(anc_img_names_arr):
            A = io.imread(DATA_DIR +"/"+ i)
            A = torch.from_numpy(A).permute(2, 0, 1) / 255.0
            A = A. to(DEVICE)
            A_enc = model(A.unsqueeze(0)) # c,h,w --> (1,c,h,w)
            encodings.append(A_enc.squeeze().cpu().detach().numpy())

        encodings = np.array(encodings)
        encodings = pd.DataFrame(encodings)
        # Convert anc_img_names to a DataFrame for concatenation
        anc_img_names_df = pd.DataFrame(anc_img_names, columns=['Anchor'])
        df_enc = pd.concat([anc_img_names_df, encodings], axis=1)

    return df_enc
DATA_DIR="/content/Market-1501-v15.09.15/query"
query_img_names = [file for file in os.listdir('/content/Market-1501-v15.09.15/query') if file.endswith('.jpg')]
query_df = get_encoding_csv(model, query_img_names)
query_df.to_csv("query_database.csv", index=False)
DATA_DIR="/content/Market-1501-v15.09.15/bounding_box_test"
gallery_img_names = [file for file in os.listdir('/content/Market-1501-v15.09.15/bounding_box_test') if file.endswith('.jpg')]
gallery_df = get_encoding_csv(model, gallery_img_names)
gallery_df.to_csv("gallery_database.csv", index=False)
query_df = pd.read_csv("query_database.csv")
gallery_df = pd.read_csv("gallery_database.csv")

def calculate_cmc(query_df, gallery_df, top_k=10):
    query_encodings = query_df.iloc[:, 1:].to_numpy()
    gallery_encodings = gallery_df.iloc[:, 1:].to_numpy()

    correct_matches = 0
    total_queries = query_df.shape[0]

    for i, row in tqdm(query_df.iterrows(), total=query_df.shape[0]):
        query_img_name = row[0]
        # Extract the ID of the person from the query image name (assuming a specific format)
        query_id = query_img_name.split('_')[0]

        query_enc = query_encodings[i].reshape(1, -1)
        distances = np.linalg.norm(gallery_encodings - query_enc, axis=1)
        closest_idx = np.argsort(distances)[:top_k]

        # Check if any of the top-k closest images have the same ID as the query image
        for idx in closest_idx:
            gallery_img_name = gallery_df.iloc[idx, 0]
            gallery_id = gallery_img_name.split('_')[0]
            if query_id == gallery_id:
                correct_matches += 1
                break  # Move to the next query if a match is found

    recall_at_k = correct_matches / total_queries
    return recall_at_k
recall_at_k_value = calculate_cmc(query_df, gallery_df, top_k=10)
print(f"Recall@10: {recall_at_k_value:.4f}")

"""<BR>
<BR>
<BR>
<BR>

## NOW TESTING MODEL FOR PERSON REIDENTIFICATION IN A VIDEO

<BR>
<BR>
"""

!pip install ultralytics

import cv2
import torch
import numpy as np
import pandas as pd
from skimage import io
from torchvision import transforms
from tqdm import tqdm
from ultralytics import YOLO
from IPython.display import display, HTML

# Load the trained re-identification model
class APN_Model(nn.Module):
    def __init__(self, emb_size=512):
        super(APN_Model, self).__init__()
        self.efficientnet = timm.create_model('efficientnet_b0', pretrained=True)
        self.efficientnet.classifier = nn.Linear(in_features=self.efficientnet.classifier.in_features, out_features=emb_size)

    def forward(self, images):
        embeddings = self.efficientnet(images)
        return embeddings

DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
model = APN_Model()
model.load_state_dict(torch.load("best_model.pt", map_location=DEVICE))
model.to(DEVICE)
model.eval()

# Load the database
df_enc = pd.read_csv("database.csv")

# Define the Euclidean distance function
def euclidean_dist(img_enc, anc_enc_arr):
    dist = np.sqrt(np.sum((img_enc - anc_enc_arr) ** 2))
    return dist

# Load the video
video_path = "Frisking Candidates.mp4"
cap = cv2.VideoCapture(video_path)

# Prepare to save the output video
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('output_video.mp4', fourcc, cap.get(cv2.CAP_PROP_FPS), (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))))

# Object detection model (YOLOv8)
model_yolo = YOLO("yolov8n.pt")

# Loop through video frames
frame_id = 0
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    results = model_yolo(frame)

    # Filter results to only include persons
    persons = [res for res in results if res.cls == 0]  # cls == 0 for 'person' class

    for person in persons:
        boxes = person.boxes.xyxy.cpu().numpy()
        classes = person.boxes.cls.cpu().numpy()
        confidences = person.boxes.conf.cpu().numpy()

        for i in range(len(boxes)):
            x1, y1, x2, y2 = boxes[i]
            person_img = frame[int(y1):int(y2), int(x1):int(x2)]

            # Preprocess the image
            person_img = cv2.cvtColor(person_img, cv2.COLOR_BGR2RGB)
            person_img = transforms.ToTensor()(person_img)
            person_img = person_img.unsqueeze(0).to(DEVICE)

            with torch.no_grad():
                person_enc = model(person_img).cpu().numpy()

            # Compare with database
            distances = []
            for j in range(df_enc.shape[0]):
                anc_enc_arr = df_enc.iloc[j, 1:].to_numpy().reshape(1, -1)
                dist = euclidean_dist(person_enc, anc_enc_arr)
                distances.append(dist)

            closest_idx = np.argmin(distances)
            threshold = 0.5  # Define your own threshold
            if distances[closest_idx] < threshold:  # Threshold to decide if it's the same person
                person_id = df_enc.iloc[closest_idx, 0]
            else:
                person_id = f'person_{len(df_enc) + 1}'
                new_entry = [person_id] + person_enc.squeeze().tolist()
                df_enc.loc[len(df_enc)] = new_entry

            # Annotate the frame
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
            cv2.putText(frame, person_id, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36, 255, 12), 2)

    # Write the annotated frame to the output video
    out.write(frame)

# Release video objects
cap.release()
out.release()

# Save the updated database
df_enc.to_csv("updated_database.csv", index=False)

# Display the saved video in the notebook
video_path = 'output_video.mp4'
display(HTML(f"""
<video width="640" height="480" controls>
  <source src="{video_path}" type="video/mp4">
</video>
"""))

import pandas as pd

class FeatureDatabase:
    def __init__(self):
        self.features = []
        self.ids = []
        self.next_id = 1

    def add_feature(self, feature):
        self.features.append(feature)
        self.ids.append(self.next_id)
        self.next_id += 1

    def find_match(self, feature, threshold=0.5):
        min_dist = float('inf')
        best_id = None

        for i, db_feature in enumerate(self.features):
            dist = np.linalg.norm(feature - db_feature)
            if dist < threshold and dist < min_dist:
                min_dist = dist
                best_id = self.ids[i]

        return best_id

feature_db = FeatureDatabase()

def compare_and_update(features, feature_db, threshold=0.5):
    person_ids = []
    for bbox, feature in features:
        person_id = feature_db.find_match(feature, threshold)
        if person_id is None:
            feature_db.add_feature(feature)
            person_id = feature_db.ids[-1]
        person_ids.append((bbox, person_id))
    return person_ids

def annotate_frame(frame, person_ids):
    for bbox, person_id in person_ids:
        x1, y1, x2, y2 = map(int, bbox)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
        cv2.putText(frame, f'ID: {person_id}', (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)
    return frame

def process_video(video_path, output_path, feature_db, interval=1):
    cap = cv2.VideoCapture(video_path)
    frames = []
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % interval == 0:
            bounding_boxes = detect_persons(frame)
            features = extract_features(frame, bounding_boxes)
            person_ids = compare_and_update(features, feature_db)
            annotated_frame = annotate_frame(frame, person_ids)
            frames.append(annotated_frame)
        frame_count += 1

    cap.release()

    height, width, layers = frames[0].shape
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(output_path, fourcc, 30, (width, height))

    for frame in frames:
        video.write(frame)

    cv2.destroyAllWindows()
    video.release()

# Process the video
video_path = 'path_to_your_video.mp4'
output_video_path = 'output_video.mp4'
process_video(video_path, output_video_path, feature_db)

def process_video(video_path, output_path, feature_db, interval=1):
    cap = cv2.VideoCapture(video_path)
    frames = []
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % interval == 0:
            bounding_boxes = detect_persons(frame)
            # Check if any persons were detected before proceeding
            if bounding_boxes.shape[0] > 0:  # Check if bounding_boxes is not empty
                features = extract_features(frame, bounding_boxes)
                person_ids = compare_and_update(features, feature_db)
                annotated_frame = annotate_frame(frame, person_ids)
                frames.append(annotated_frame)
        frame_count += 1

    cap.release()

    # Handle the case when no frames were captured
    if frames:
        height, width, layers = frames[0].shape
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video = cv2.VideoWriter(output_path, fourcc, 30, (width, height))

        for frame in frames:
            video.write(frame)

        cv2.destroyAllWindows()
        video.release()
    else:
        print("No frames were processed. Check the video file and detection process.")

# Process the video
video_path = '/Frisking Candidates.mp4'
output_video_path = '/content/output_video111.mp4'
process_video(video_path, output_video_path, feature_db)

def reassemble_video(frames, output_path, fps=30):
    height, width, layers = frames[0].shape
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    for frame in frames:
        video.write(frame)

    cv2.destroyAllWindows()
    video.release()

video_path = '/Frisking Candidates.mp4'
output_video_path = '/content/output_video.mp4'
frames = extract_frames(video_path, interval=5)  # Extract frames at every 5th frame

annotated_frames = []

for frame in frames:
    bounding_boxes = detect_persons(frame)
    features = extract_features(frame, bounding_boxes)
    person_ids = match_persons(features)
    annotated_frame = annotate_frame(frame, person_ids)
    annotated_frames.append(annotated_frame)

reassemble_video(annotated_frames, output_video_path)



