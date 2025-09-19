### Assignment 5 - MNIST model

#### 1. Requirements
Build a model which achieves the following on the MNIST dataset:
- 99.4% validation/test accuracy
- Less than 20k Parameters
- Less than 20 Epochs
- Have used BN, Dropout
- (Optional): a Fully connected layer or, have used GAP

#### 2. Experiments
The best model from session 4 experiments was under 20K parameters, so the same was used to start off the experiments. 

|#  | Changes	                                                | Model Params	|  Train accuracy |	Test Accuracy |	Notebook | Notes |
|--| ------------------------------------------------------- | -------- | --------- | --------- | ---------- | ------- |
|1. | Ran best session4 model with 20 epochs, without batchnorm, dropout or GAP | 17,490 |	99.01 |	99.19 | [Iteration1](https://github.com/smitasasindran/era4/blob/master/Session5/ERA4_Session_5_Iteration1.ipynb) | Can get better. Has a FC layer |
|2. | Added batchnorm  | 17,666	| 99.49 |	99.42 | [Iteration2](https://github.com/smitasasindran/era4/blob/master/Session5/ERA4_Session_5_Iteration2.ipynb) | Slight overfitting observed |
|3. | Changed to Adam optimizer | 17,666 |	99.45 |	99.44 | [Iteration3](https://github.com/smitasasindran/era4/blob/master/Session5/ERA4_Session_5_Iteration3.ipynb) | Still overfitting |
|4. | Added dropout to one cnn layer with highest parameter (conv3 with 4k params), switched back to SGD | 17,666 |	99.4 |	99.47 |[Iteration4](https://github.com/smitasasindran/era4/blob/master/Session5/ERA4_Session_5_Iteration4.ipynb) |  Did not make much difference |     





#### 3. Model summary (BN, Dropout layers) - Iteration 4


```
----------------------------------------------------------------
        Layer (type)               Output Shape         Param #
================================================================
            Conv2d-1            [-1, 8, 26, 26]              80
       BatchNorm2d-2            [-1, 8, 26, 26]              16
            Conv2d-3           [-1, 16, 24, 24]           1,168
       BatchNorm2d-4           [-1, 16, 24, 24]              32
            Conv2d-5           [-1, 32, 22, 22]           4,640
       BatchNorm2d-6           [-1, 32, 22, 22]              64
           Dropout-7           [-1, 32, 22, 22]               0
            Conv2d-8            [-1, 8, 22, 22]             264
            Conv2d-9             [-1, 16, 9, 9]           1,168
      BatchNorm2d-10             [-1, 16, 9, 9]              32
           Conv2d-11             [-1, 16, 7, 7]           2,320
      BatchNorm2d-12             [-1, 16, 7, 7]              32
           Linear-13                   [-1, 10]           7,850
================================================================
Total params: 17,666
Trainable params: 17,666
Non-trainable params: 0
----------------------------------------------------------------
Input size (MB): 0.00
Forward/backward pass size (MB): 0.64
Params size (MB): 0.07
Estimated Total Size (MB): 0.71
----------------------------------------------------------------
```



#### 4. Test Logs - Iteration 4


```
Epoch 17
Train: Loss=0.1424 Batch_id=468 Accuracy=99.42: 100%|██████████████████████████████████████████████████████████████████████████████████████████| 469/469 [00:05<00:00, 83.43it/s]
Test set: Average loss: 0.0001, Accuracy: 9945/10000 (99.45%)

Epoch 18
Train: Loss=0.1595 Batch_id=468 Accuracy=99.44: 100%|██████████████████████████████████████████████████████████████████████████████████████████| 469/469 [00:05<00:00, 83.14it/s]
Test set: Average loss: 0.0001, Accuracy: 9945/10000 (99.45%)

Epoch 19
Train: Loss=0.1543 Batch_id=468 Accuracy=99.52: 100%|██████████████████████████████████████████████████████████████████████████████████████████| 469/469 [00:05<00:00, 82.47it/s]
Test set: Average loss: 0.0001, Accuracy: 9948/10000 (99.48%)

Epoch 20
Train: Loss=0.1313 Batch_id=468 Accuracy=99.40: 100%|██████████████████████████████████████████████████████████████████████████████████████████| 469/469 [00:05<00:00, 82.82it/s]
Test set: Average loss: 0.0001, Accuracy: 9947/10000 (99.47%)

```






**Notes**:
- Add Batchnorm to all layers except the last one, and 1x1 layer
- Dropout should be applied after activation is applied
