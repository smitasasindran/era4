## Continuous Control Navigation using TD3

This project implements **Twin Delayed Deep Deterministic Policy Gradient (TD3)** to control a simulated car navigating in a 2D environment.  
The original codebase used 5 discrete steering actions and one fixed speed. This has been extended to support true continuous control for both steering and throttle using TD3.   
[T3D sample code](https://colab.research.google.com/drive/1bgmBUB6YuC-LuG-3X5QAXVEaWHaZEEsB?usp=sharing#scrollTo=u5rW0IDB8nTO)

[Video](https://www.youtube.com/watch?v=ZRQ_JEI_UvU)

---

### Overview

- **Algorithm**: TD3 (Twin Delayed DDPG)
- **Action Space**: Continuous  
  - Steering ∈ `[-1, 1]`  
  - Throttle ∈ `[-1, 1]` (rescaled to `[0, 1]` for the environment)
- **Environment**: Custom 2D car navigation simulator
- **Framework**: PyTorch

The goal is to learn smooth, stable navigation behavior without oscillations, limit cycles, or discrete-action artifacts.

---

### What is TD3?

TD3 is an off-policy, actor–critic reinforcement learning algorithm designed for continuous control tasks.  
It improves upon DDPG by addressing overestimation bias and training instability.

#### Key ideas in TD3

1. **Twin Critics**  
Two Q-networks (`Q1`, `Q2`) are trained simultaneously.  
The smaller of the two estimates is used for target computation:

2. **Delayed Policy Updates**  
The actor is updated less frequently than the critics, improving stability.

3. **Target Policy Smoothing**  
Noise is added to target actions to prevent overfitting to narrow Q-function peaks.

TD3 is especially well-suited for robotics and vehicle control problems where actions are naturally continuous.

---

### Integration into the Existing Codebase

The original RL setup used:
- Discrete steering actions (e.g. left / right / straight / sharp left / sharp right)
- Constant vehicle speed
- DQN-style assumptions

To integrate TD3, the following structural changes were made:


##### 1. Continuous Action Representation

The action was redefined as a 2D continuous vector:
```
action = [steer, throttle]

steer ∈ [-1, 1] controls left/right turning 
throttle ∈ [-1, 1] controls speed (later rescaled) 
```
The actor network outputs actions using a tanh activation to naturally bound them.

##### 2. Separation of Learning Space and Physics Space
A key design choice was to keep the learning space normalized:

- Actor output, critic input, and replay buffer actions remain in [-1, 1]
- Rescaling is done only when stepping the environment
```commandline
steer = a[0]
throttle = (a[1] + 1) / 2   # [-1,1] → [0,1] for physics
```
This separation keeps learning stable while allowing physically meaningful controls.


##### 3. Environment Physics Update
The environment was modified to use continuous dynamics: 
- Steering directly controls heading change
- Throttle controls speed magnitude
- Position updates use smooth trigonometric motion
This removed discrete turn quantization and enabled smooth trajectories.  


##### 4. Critic Architecture Update

The critic networks were updated to accept:
```commandline
[state, action] → Q-value
```

Actions are treated as floating-point tensors and concatenated with the state before being passed through the network.


##### 5. Issues faced

1. Circling / Limit-Cycle Behavior
The agent initially learned to drive in tight circles due to:
- Fixed speed
- No penalty for excessive steering
- Lack of progress-based reward

Fixes:
- Introduced continuous throttle
- Added steering penalty
- Rewarded forward progress toward the goal

2. Incorrect Action Scaling in Replay Buffer
Storing rescaled throttle values ([0,1]) in memory caused learning instability.
Fix: 
Replay buffer stores raw normalized actions ([-1,1]), rescaling happens only at the environment boundary.

3. Agent not learning well/ taking sharper turns
Agent was learning very slowly, and sometimes the speed would be high during sharp turns, causing it to overshoot and crash
Fix: 
Update the reward structure, reduced max speed and max turn values for better control. Agent now slows down at sharp turns.


