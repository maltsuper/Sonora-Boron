# Sonora
Sonora

Text to Synth Application


History
19.11.26: Uses a local instance of ollama and alters parameters on the synthesiser plugin 'vital'


Sonora.py breakdown
Defined classes 'Osc' and 'Sound'.

Classes
    'Osc': object which describes a basic wave shape along with some basic parameters.
    'Sound': object which describes the characteristics of a sound from 0 to 1.

System Prompt
    The system prompt which was pass to ollama upon starting each instance. The examples are the actual glue to this; they turn it from a framework of code to something that can actually interpret and make sound.

Functions
    'set_osc'  
        inputs: 
                v: vital settings dictionary (to translate our 0 to 1 weights to vital json numbers)
                i: which osciallator is being created (its number)
                o: the actual oscillator objects
        outputs: 
                none (it just alters the object that it was passed)
    'ask'
        inputs: 
                description: the users message to the ai (describing the sound)
        outputs:
                the json file of the synth parameters
    'knob_conversion'
        inputs:
                x: our weights from 0 to 1
                lo: vital parameters lower bound
                hi: vital parameters upper bound 
        outputs: 
                new weight
                
    'to_vital' 

    'main'

