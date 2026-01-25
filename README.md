# MazeTilt
This project was developed as part of the Multisensory Interactive Systems course at the University of Trento.  
Authors:
- Cappellaro Nicola
- Zannoni Riccardo

## Implementation overview
The system implements a tilt-controlled 3D labyrinth game with visual, audio, and haptic feedback.
A Teensy-based controller acquires accelerometer data and communicates with the system via OSC.
The architecture is distributed, with a PC and a Raspberry Pi connected through a router.
Game logic and real-time rendering run on the PC, while audio output and hardware interfaces are handled by the Raspberry Pi.
Visual feedback is displayed on the PC, while audio and haptic feedback are delivered through devices connected to the Raspberry Pi.  
A more detailed explanation of the system is provided in the report document, together with a demonstration video.

## How to run

- Connect the Raspberry Pi to the router via Wi-Fi.
- Connect the PC to the same router via Wi-Fi.
- On the Raspberry Pi, run the following Pure Data patches:
  - Accelerometer & communication:  
    `Pd_serial_communication_send_receive/Main_Pd_serial_communication_send_receive.pd`
  - Audio synthesis:  
    `PureDataAudio/audioPatch.pd`
- The visual interface will be displayed on the PC. The game is controlled using the gamepad connected to the Raspberry Pi:
  - Input:
    - gamepad → Raspberry Pi (accelerometer)
  - Output:
    - visual feedback → PC
    - audio feedback → Raspberry Pi (loudspeaker)
    - haptic feedback → Raspberry Pi (ERM motor of the gamepad)
    
NB: The system can also be run entirely on a single PC for convenience.
In this case, connect all devices (gamepad and sound card) directly to the PC, run the Pure Data patches locally (adapting the serial port), and execute `maze_tilt.py` using the localhost IP address (`127.0.0.1`).