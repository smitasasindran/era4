### Assignment 16 - RL

#### 1. Requirements

    1. Create a new map of some other city for the code shared above      
    2. Add a DNN with 1 more FC layer.   
    3. Your map must have 3 targets A1>A2>A3, and your car/robot/object must target these alternatively.    
    4. Train your best model, upload a video on YouTube, and share the URL   
    5. Answer these questions in Assignment-Solution:     
        - What happens when "boundary-signal" is weak when compared to the last reward?  
        - What happens when Temperature is reduced?   
        - What is the effect of reducing (gamma)?   
    6. Heavy marks for creativity, map quality, targets, and other things. If you use the same maps or have just replicated shared code, you will get 0 for this assignment and a -50% advance deduction for the next assignment.   



#### 2. Experiments

2.1 Running class code with some reasonable hyperparameter values  
Model was running on the correct roads after a while, but did not go to the targets all the time

2.2 Adding logs to see what model is doing  
Rewards were incorrect and very high. Car was being incentivized to reach obstacles

2.3 Rewards  
Changed the rewards to consider sensor values correctly. Penalize if the minimum sensor value is closer to 0 (obstacle). 
Also added a reward based on delta distance - i.e. add a small reward if car is moving towards the goal. 
Model runs for longer episodes, rewards are not too negative or too positive, and hits all three targets at frequent intervals.   
However it is still taking a long time to finally hit all 3 targets correctly. It seems to forget the episodes/steps it has learnt, even though the priority memory is full and being used completely.   

2.4 Changing hyperparams: Gamma, LR   
- Gamma: Discount factor for future rewards      
Gamma was earlier set to 0.9, increased this to 0.99 so that it gives even higher weightage to future steps.    
After changing gamma, the good episodes were repeated more frequently, especially from from start point to target A, and target A to target B. Going from target B to target C was still error prone   
- LR:  
Initial LR was set to 0.001. This was probably too aggressive.      
Reducing LR to 0.0001: Model crashed a lot during the first 2500 episodes, then learnt to stay on the road for much longer steps. However it seemed to prioritize running for more steps rather than reaching the targets, so it took the longer route to the targets, especially target A.    
Changing LR to 0.0003: A bit better than 0.0001. Spends around 2000 episodes near starting point   
Changing LR to 0.0005: Spends around 1500 short episodes near starting point. Staying with 0.0003 to start with
  (Lower LR leads to better retention)   
- Batch Size:  
Kept LR as 0.0003 and changed batch size from 256 to 128. Spends around 2000+ episodes crashing near the starting point, then becomes quite stable and goes on much longer episode runs in the right direction. Not quite sure why this helped as much as it did.   

After these changes, the model training was faster, and it hit all targets correctly much early on (~3000 episodes). The model also remembered past successful episodes. However while it was able to repeat the Target A -> B steps correctly, it would miss out target B -> C, even though they were close by with less steps.        

2.5: Final Reward   
Earlier, each target was getting a high reward of 100. The model then treats all targets the same, so it does not consider the final target to be the end goal and goes on longer routes especially from 2nd to 3rd target. Now another large reward (+100) is added when final target is reached. The Target A->B->C route is now repeated very frequently.  

2.6: Assignment requirements:  
- Trying with different maps   
The previous tests were done with a circular map, which did not have a lot of sharp angles. So a turn angle of 10 degrees was not sufficient.
With the new map which had a lot more sharp angles, the turn angle had to be increased.   
- Adding another FC layer to DriverDNN  
Didn't make a noticable difference.  
- Speed + Batch size 
Increasing the speed reduced the number of steps to be taken, which in turn led to greater retention of the correct sequence of steps.      
Increased the batch size from 128 to 256 and noticed the good episodes repeating more frequently.   

