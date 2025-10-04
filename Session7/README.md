### Assignment 7 - CIFAR-10


#### 1. Requirements
Write a new network that: 

    1. works on CIFAR-10 Dataset
    2. has the architecture to C1C2C3C40 (No MaxPooling, but convolutions, where the last one has a stride of 2 instead) (NO restriction on using 1x1) (If you can figure out how to use Dilated kernels here instead of MP or strided convolution, then 200pts extra!)
    3. total RF must be more than 44
    4. One of the layers must use Depthwise Separable Convolution
    5. One of the layers must use Dilated Convolution
    6. use GAP (compulsory):- add FC after GAP to target #of classes (optional)
    7. Use the albumentation library and apply:
       - horizontal flip
       - shiftScaleRotate
       - coarseDropout (max_holes = 1, max_height=16px, max_width=16, min_holes = 1, min_height=16px, min_width=16px, fill_value=(mean of your dataset), mask_fill_value = None)
    8. achieve 85% accuracy, as many epochs as you want. Total Params to be less than 200k.
    9. Make sure you're following code-modularity (else 0 for full assignment) 


#### 2. Experiments

Iterative experiments are mentioned below:   

|#  | Changes	                                                | Model Params	|  Train accuracy |	Test Accuracy |	Notebook | 
|--| ------------------------------------------------------- | -------- | --------- | --------- | ---------- |
|1. | Initial - trying with a small basic model. Architecture: C1C2C3C40. No MaxPooling, has 1x1, GAP, no FC  | 34,136	|  68.64 |	67.75 | [Iniital](https://github.com/smitasasindran/era4/blob/session7/Session7/ERA4_Session7_Iteration1.ipynb)	  | 
|2. | Updated model architecture - Added more kernels, but same architecture as before  | 134,320 | 80.69 |	78.66 | [Iteration2](https://github.com/smitasasindran/era4/blob/session7/Session7/ERA4_Session7_Iteration2.ipynb)  |
|3. | Added Depthwise Separable Conv, Dilated Conv, RF=45  | 99,408 |	86.76 |	85.49 | [Iteration3](https://github.com/smitasasindran/era4/blob/session7/Session7/ERA4_Session7_Iteration3.ipynb) |
|4. | Added albumentations transforms | 99408 |	83.90 |	85.40 | [Iteration3](https://github.com/smitasasindran/era4/blob/master/Session4/ERA4_Session_4_Iteration4.ipynb) |
|5. | Moved to modular code | 99408 |	83.70 |	85.03 | [Final](https://github.com/smitasasindran/era4/blob/session7/Session7/ERA4_Session7_Final.ipynb) |



#### 3. Best Architecture
