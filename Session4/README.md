### Assignment 4 - MNIST model

#### 1. Requirement: 
Make an MNIST-based model that has the following characteristics:
 - Has fewer than 25000 parameters
 - Gets to test accuracy of 95% or more in 1 Epoch



#### 2. Experiments:

The best experiments are mentioned below. A few of the experiments were merged into the same colab file for the sake of brevity:   

|#  | Changes	                                                | Model Params	|  Train accuracy |	Test Accuracy |	Notebook | 
|--| ------------------------------------------------------- | -------- | --------- | --------- | ---------- |
|1. | Base version - fix model params                         | 593,200	|  9.97 |	9.87 | [Base_notebook](https://github.com/smitasasindran/era4/blob/master/Session4/ERA4_Session_4_Base_notebook.ipynb)	  | 
|2. | Updated model architecture - added maxpooling after 9x9 RF, added 1x1 before MP, changed LR=0.01. Batch size 512, batch shuffle True, removed RandomCrop and Rotation transforms  | 27,650 | 23.56 |	54.85 | [Iteration1](https://github.com/smitasasindran/era4/blob/master/Session4/ERA4_Session_4_Iteration1.ipynb)  |
|3. | Batch shuffle false, put back rotation and randomcrop transforms, reduced batch size to 128, LR same as before (0.01). Fixed a random seed | 27650 |	62.53 |	95.45 | [Iteration2](https://github.com/smitasasindran/era4/blob/master/Session4/ERA4_Session_4_Iteration2.ipynb) |
|4. | Reduced kernel size in the conv layer before FC layer from 32 to 16, which reduced number of params from 15690 to 7850 in fc layer itself | 17,490 |	72.55 |	95.89 | [Iteration3](https://github.com/smitasasindran/era4/blob/master/Session4/ERA4_Session_4_Iteration3.ipynb) |


#### 3. Best Architecture

```
class Net(nn.Module):
    # Define the structure of the NN

    def __init__(self):
        super(Net, self).__init__()
        self.conv1 = nn.Conv2d(1, 8, kernel_size=3)
        self.conv2 = nn.Conv2d(8, 16, kernel_size=3)
        self.conv3 = nn.Conv2d(16, 32, kernel_size=3)
        self.conv4 = nn.Conv2d(32, 8, kernel_size=1)
        self.conv5 = nn.Conv2d(8, 16, kernel_size=3)
        self.conv6 = nn.Conv2d(16, 16, kernel_size=3)
        self.fc1 = nn.Linear(784, 10)

    def forward(self, x):
        x = F.relu(self.conv1(x), 2)    # 512 x 8 x 26 x 26
        x = F.relu(self.conv2(x), 2)    # 512 x 16 x 24 x 24
        x = F.relu(self.conv3(x))       # 512 x 32 x 22 x 22
        x = self.conv4(x)               # 512 x 8 x 22 x 22
        x = F.relu(F.max_pool2d(x, 2))  # 512 x 8 x 11 x 11

        x = F.relu(self.conv5(x))  # 512 x 16 x 9 x 9
        x = F.relu(self.conv6(x))  # 512 x 32 x 7 x 7
        x = x.view(-1, 784)
        x = self.fc1(x)
        return x
```


**Notes**:
  - Adding transformations increased the accuracy by a large margin
  - Reducing LR and batch size helped increase accuracy
  - 1 x 1 should be before maxpooling, not after -- compress original features better
  - relu after maxpooling, or relu before maxpooling have same output
  - A second 1x1 added just before FC layer decreased the accuracy drastically
  - CrossEntropy loss already adds softmax, so no need of doing it in the model
