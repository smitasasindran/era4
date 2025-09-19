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
|1. | Ran best session4 model with 20 epochs, without batchnorm, dropout or GAP | 17,490 |	99.01 |	99.19 | [Iteration1]() | Can get better. Has a FC layer |
|2. | Added batchnorm  | 17,666	| 99.49 |	99.42 | [Iteration2]() | Slight overfitting observed |
|3. | Changed to Adam optimizer | 17,666 |	99.45 |	99.44 | [Iteration3]() | Still overfitting |
|4. | Added dropout | 





#### 



**Notes**:
- Add Batchnorm to all layers except the last one, and 1x1 layer
- Dro
- Dropout should be applied after activation is applied
