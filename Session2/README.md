## Background Extractor

This is a Streamlit app which extracts the background from either:   
1. A set of images
2. A video file
3. RTSP stream
The final background image can then be downloaded.


### Usage
Select an Input Mode, and then a Background Estimation Method.

There are three options for input mode:  
 - If 'Image Directory' is selected, provide path to a local directory which contains a batch of images from the same source. The images should be of the same resolution. A single background image will be created.
 - If 'Video File' is selected, upload a video. A Single background image will be created.
 - If 'RTSP Stream' option is selected, the live view of the stream will be displayed, along with the most recent background extracted, as well as the foreground mask.

For background estimation method:    
- **Median** – Robust to moving objects, good general choice.   
- **Mode** – Picks the most frequent pixel value, useful if background repeats consistently.   
- **MOG2** – OpenCV's adaptive background subtractor, handles gradual lighting changes.   


### How to run on local system   
Install cv2 and streamlit, then do

`streamlit run background_creator.py   `

Go to http://localhost:8501/


### SAM deployment
- Build a lambda layer for opencv-headless on Cloudshell, and save it to s3 (size limitations). Then create a lambda layer
- Install aws-cli and sam-cli, for deploying flask application to aws lambda
- Do 'sam build' in the flask app main directory
- Configure aws cli, and create a new profile
- Then do 'sam deploy --guided --profile myprofile --region <region>'



