import json, re #Json to write and read json, 
#re (regular expression), to search and clean up text with patterns
from pathlib import Path
# Lets us handle file and folder locations, can build paths with / e.g. home/documents
from pydantic import BaseModel, Field
# pydantic pets us describe the exact shape our data must take
# 'BaseModel' is the start for making the shapes, 'Field' lets us attach a description to pass to AI as hints
import ollama
# Lets us send messages to Ollama and brings the replies back
from typing import Literal

MODEL = "qwen2.5:3b"
# Just storing the name of the model we use in a variable
VITAL_DIR = Path.home() / "Documents" / "Vital"
# Path.home is (C:\Users\Name)
OUT_DIR = VITAL_DIR / "Sonora" / "Presets"
# Var to build the folder where new presets will be saved
WAVE_FRAMES = {"sine": 15, "triangle": 80, "saw": 112,
               "square": 160, "pulse": 205, "thin pulse": 240}

class Osc(BaseModel):
    on: bool = Field(description="Whether this oscillator plays at all.")
    wave: Literal["sine", "triangle", "saw", "square", "pulse", "thin pulse"] = Field(
        description="Waveform. sine = pure, soft, round; triangle = gentle, hollow, flute-like; "
                    "saw = bright, buzzy, rich; square = hollow, woody, reedy; "
                    "pulse = nasal, funky, retro; thin pulse = thin, buzzy, chiptune")
    level: float = Field(description="Volume in the mix. Only has an effect when oscillator is 'on'. 0 = silent, 1 = full")
    octave: int = Field(description="Octave shift from -2 to 2. -1 = an octave lower, often used in sub layer. +1 = an octave higher, usually used in bright chimes.")
    detune: float = Field(description="Slight mistuning against the other oscillators. 0 = in tune, 1 = very detuned.")
    width: float = Field(description="Unison thickness. 0 = thin single voice, 1 = large multiple layers stacked")

class Sound(BaseModel):
# Defining a new data shape called Sound, using 'BaseModel' in ()
# means Sound gets all of Pydantic's data checking powers
    name: str = Field(description="2-3 plain words describing the sound, ending with its type, e.g. 'Warm Slow Pad'. No poetic or made-up names")
    # this means all 'Sounds' must have a name, and the desc. is info for the AI
    osc1: Osc
    osc2: Osc
    attack: float = Field(description="Attack: time for a sound to reach full volume after a key press. 0 = instant, 1 = slow fade in")
    decay: float = Field(description="Decay: time and rate to drop from full volume to sustain level. 0 = drops to sustain level instantly after the hit, 1 = falls slowly to the sustain level")
    sustain: float = Field(description="Sustain: volume level held while the key is down. 0 = Fades to silence, 1 = stays at full volume")
    release: float = Field(description="Release: how long the sound rings after the key is let go. 0 = sound stops instantly, 1 = sound continues to play for an extended duration after key is released")
    brightness: float = Field(description="Brightness: how much high end comes through the filter. 0 = dark and muffled, 1 = bright, open, airy, sparkly. Dreamy and floating sounds are usually bright.")
    resonance: float = Field(description="Resonance: emphasis at the filter cutoff. 0 = smooth, 1 = sharp, squelchy peak")
    reverb: float = Field(description="Reverb: amount of room or space. 0 = dry and close, 1 = huge and washy")
    chorus: float = Field(description="Chorus: shimmering, widening effect. 0 = off, 1 = strong and lush")
    drive: float = Field(description="Drive: Distortion control. 0 = clean, 1 = gritty")

SYSTEM = """
You are a synth sound designer. Turn the description into knob positions from 0 to 1. Octave is a whole number from -2 to 2.
Each sound has two oscillators: osc1 is the main tone, osc2 adds a layer (an octave down for depth, an octave up for tinglyness, or detuned for grit), or is off.
Examples:
"warm dreamy pad" -> name "Warm Slow Pad": osc1 (on, saw, level 0.8, octave 0, detune 0, width 0.5), osc2 (on, triangle, level 0.45, octave -1, detune 0.1, width 0.2), attack 0.6, decay 0.6, sustain 0.8, release 0.7, brightness 0.4, resonance 0.1, reverb 0.7, chorus 0.5, drive 0
"smooth deep pad" -> name "Smooth Dark Pad": osc1 (on, triangle, level 0.8, octave 0, detune 0, width 0.4), osc2 (on, sine, level 0.5, octave -1, detune 0, width 0), attack 0.5, decay 0.6, sustain 0.85, release 0.65, brightness 0.3, resonance 0.05, reverb 0.55, chorus 0.4, drive 0
"bright airy pad" -> name "Bright Airy Pad": osc1 (on, saw, level 0.8, octave 0, detune 0, width 0.7), osc2 (on, sine, level 0.35, octave 1, detune 0.15, width 0.5), attack 0.45, decay 0.5, sustain 0.9, release 0.75, brightness 0.75, resonance 0.15, reverb 0.8, chorus 0.6, drive 0
"dark ambient drone" -> name "Dark Wide Drone": osc1 (on, saw, level 0.8, octave 0, detune 0, width 0.8), osc2 (on, square, level 0.6, octave -1, detune 0.3, width 0.6), attack 0.9, decay 0.8, sustain 1, release 1, brightness 0.2, resonance 0.15, reverb 0.9, chorus 0.3, drive 0.1
"plucky bass" -> name "Short Pluck Bass": osc1 (on, saw, level 0.9, octave 0, detune 0, width 0.1), osc2 (on, sine, level 0.5, octave -1, detune 0, width 0), attack 0, decay 0.3, sustain 0.1, release 0.15, brightness 0.35, resonance 0.4, reverb 0.05, chorus 0, drive 0.3
"deep sub bass" -> name "Clean Sub Bass": osc1 (on, sine, level 0.9, octave -1, detune 0, width 0), osc2 (off, sine, level 0, octave 0, detune 0, width 0), attack 0, decay 0.5, sustain 0.9, release 0.2, brightness 0.1, resonance 0, reverb 0, chorus 0, drive 0.05
"gritty reese bass" -> name "Gritty Detuned Bass": osc1 (on, saw, level 0.8, octave 0, detune 0, width 0.7), osc2 (on, saw, level 0.8, octave 0, detune 0.6, width 0.5), attack 0.02, decay 0.5, sustain 0.9, release 0.25, brightness 0.45, resonance 0.2, reverb 0.05, chorus 0.1, drive 0.6
"acid squelch bass" -> name "Resonant Acid Bass": osc1 (on, saw, level 0.9, octave 0, detune 0, width 0), osc2 (off, sine, level 0, octave 0, detune 0, width 0), attack 0, decay 0.25, sustain 0.3, release 0.1, brightness 0.5, resonance 0.9, reverb 0.05, chorus 0, drive 0.4
"bright supersaw lead" -> name "Wide Supersaw Lead": osc1 (on, saw, level 0.9, octave 0, detune 0, width 1), osc2 (on, saw, level 0.5, octave 1, detune 0.1, width 0.8), attack 0.02, decay 0.5, sustain 0.8, release 0.3, brightness 0.85, resonance 0.2, reverb 0.3, chorus 0.2, drive 0.1
"soft mellow lead" -> name "Soft Mellow Lead": osc1 (on, triangle, level 0.85, octave 0, detune 0, width 0.1), osc2 (off, sine, level 0, octave 0, detune 0, width 0), attack 0.1, decay 0.5, sustain 0.8, release 0.3, brightness 0.4, resonance 0.1, reverb 0.35, chorus 0.2, drive 0
"retro chiptune lead" -> name "Thin Retro Lead": osc1 (on, thin pulse, level 0.85, octave 0, detune 0, width 0), osc2 (off, sine, level 0, octave 0, detune 0, width 0), attack 0, decay 0.4, sustain 0.7, release 0.1, brightness 0.8, resonance 0.1, reverb 0.15, chorus 0, drive 0
"short bright pluck" -> name "Bright Short Pluck": osc1 (on, saw, level 0.85, octave 0, detune 0, width 0.3), osc2 (on, square, level 0.4, octave 1, detune 0.05, width 0.2), attack 0, decay 0.25, sustain 0, release 0.2, brightness 0.8, resonance 0.25, reverb 0.3, chorus 0.1, drive 0
"soft electric piano keys" -> name "Soft Electric Keys": osc1 (on, sine, level 0.85, octave 0, detune 0, width 0.15), osc2 (on, triangle, level 0.3, octave 1, detune 0.05, width 0), attack 0.01, decay 0.6, sustain 0.3, release 0.4, brightness 0.45, resonance 0.1, reverb 0.3, chorus 0.5, drive 0.05
"lo-fi muffled keys" -> name "Muffled Lo-Fi Keys": osc1 (on, triangle, level 0.85, octave 0, detune 0.1, width 0.1), osc2 (on, sine, level 0.3, octave -1, detune 0.15, width 0), attack 0.02, decay 0.55, sustain 0.4, release 0.35, brightness 0.2, resonance 0.1, reverb 0.4, chorus 0.4, drive 0.25
"aggressive distorted stab" -> name "Distorted Wide Stab": osc1 (on, square, level 0.85, octave 0, detune 0, width 0.6), osc2 (on, saw, level 0.7, octave 0, detune 0.4, width 0.5), attack 0, decay 0.2, sustain 0.2, release 0.15, brightness 0.7, resonance 0.3, reverb 0.1, chorus 0, drive 0.9
"ethereal floating dreamy pad" -> name "Airy Floating Pad": osc1 (on, triangle, level 0.8, octave 0, detune 0, width 0.35), osc2 (on, sine, level 0.4, octave 1, detune 0.1, width 0.3), attack 0.5, decay 0.6, sustain 0.8, release 0.75, brightness 0.7, resonance 0.1, reverb 0.85, chorus 0.6, drive 0
"""

def set_osc(v, i, o):
    # v = vital settings dict, i = the oscillator number, o = the oscillator object
    p = f"osc_{i}_"
    v[p + "on"] = 1.0 if o.on else 0.0
    v[p + "wave_frame"] = float(WAVE_FRAMES[o.wave])
    v[p + "level"] = knob_conversion(o.level, 0.0, 1.0)
    v[p + "transpose"] = float(max(-2, min(2, o.octave)) * 12) # to go from octaves to semitones
    v[p + "tune"] = knob_conversion(o.detune, 0.0, 0.3)
    v[p + "unison_voices"] = round(knob_conversion(o.width, 1, 16))
    v[p + "unison_detune"] = knob_conversion(o.width, 0.0, 6.0)

def ask(description: str) -> Sound: # function called 'ask' with a type hint to return a Sound
    # Message: the conversation we send the model (written as a list where each message is a small dictionary)
    # Role: who's speaking?, "system" = background instructions, "user" = the person asking, "assistant" = the AI's own replies
    # Content = the actual text
    # Sound.model_json_schema() turns our 'Sound' class into a JSON schema i.e. a machine readable format
    # Options holds extra settings for how our model generates text
    # Temperature controls randomness of the model. 0 = picks the most likely answer each time, 1 = takes more chances
    r = ollama.chat(model=MODEL,
                    messages=[{"role": "system", "content":  SYSTEM}, 
                              {"role": "user", "content": description}],
                    format=Sound.model_json_schema(),
                    options={"temperature": 0.3}
                    )
    return Sound.model_validate_json(r.message.content)

def knob_conversion(x, lo, hi):
    # Converts our AI's 0-1 numver into Vital's real range (like turning a knob)
    x = min(max(x, 0.0), 1.0)
    return lo + (hi - lo) * x

def to_vital(s: Sound, base: dict, description: str) -> dict:
    # slave to the baseline, stranger to the daytime
    # json.dumps turns the dictionary into a JSON string
    # json.loads turns JSON string into a new dictionary
    p = json.loads(json.dumps(base)) # Deep copy so that when we make changes to the dictionary it doesn't affect the OG
    v = p["settings"] # A shortcut to the preset's 775 settings.

    #here we set a single vital setting 
    v["env_1_attack"]  = knob_conversion(s.attack, 0.0, 1.4)
    v["env_1_decay"]   = knob_conversion(s.decay, 0.27, 1.65)
    v["env_1_sustain"] = knob_conversion(s.sustain, 0.0, 1.0)
    v["env_1_release"] = knob_conversion(s.release, 0.0, 1.55)
    v["filter_1_on"] = 1.0
    v["filter_1_cutoff"]    = knob_conversion(s.brightness, 20, 130)
    v["filter_1_resonance"] = knob_conversion(s.resonance, 0.0, 0.9)
    set_osc(v, 1, s.osc1)
    set_osc(v, 2, s.osc2)
    v["reverb_on"] = 1.0 if s.reverb > 0.02 else 0.0
    v["reverb_dry_wet"] = knob_conversion(s.reverb, 0.0, 0.6)
    v["chorus_on"] = 1.0 if s.chorus > 0.02 else 0.0
    v["chorus_dry_wet"] = knob_conversion(s.chorus, 0.0, 1.0)
    v["distortion_on"] = 1.0 if s.drive > 0.02 else 0.0
    v["distortion_drive"] = knob_conversion(s.drive, 0.0, 30.0)
    p["author"] = "Sonora"
    p["comments"] = description
    return p

def tweak_sound(current_sound, description):

    new_sound = current_sound

    return new_sound

def save_sound(sound, base, description):
    print(f"\n{sound.model_dump()}")    # model_dump() turns the Sound back into a plain dict, for print checking.
    name = re.sub(r"[^\w\- ]", "", sound.name).strip() or "Sonora Sound"
                                        #re.sub(pattern, "",  s.name) deletes every character that matches the pattern
                                        # the pattern: "[^\w\- ]" means every character that is not "^" a letter, digit, or underscore "\w", "\-" so "/,\,.,:, etc" are removed
                                        # we use "r" to make python treat the string as a raw string
                                        # .strip() trims leftover spaces at the ends
                                        # "or "Sonora Sound"" if nothing is left 
    n = 1                               # Numbers the synths incase they have the same name
    while (OUT_DIR / f"{name} {n:02d}.vital").exists(): # While they have the same name create a synth with the next number
        n += 1                                                         
    out = OUT_DIR / f"{name} {n:02d}.vital"
                                # builds the full path to the file to save

    out.write_text(json.dumps(to_vital(sound, base, description)), encoding="utf-8")
                                        # to_vital(s, base, description) = builds the new preset dict from the AI's knob positions and our base preset
                                        # json.dumps(...) turns the dict into JSON text
                                        # out.write_text(..., encoding="utf-8")
    print(f"Saved: {out}")

def main():

    ollama_open_qs = input("Have you opened ollama? (y/n)")
    assert ollama_open_qs.lower() == "y", "Ollama must be open."
                                    # VITAL_DIR.rglob searches the Vital folder and all subfolders for a file with the name 'Sonora Base.vital'
                                    # rglob produces mathces one at a time, next(...) takes the first one, None is the fallback
    base_path = next(VITAL_DIR.rglob("Sonora Base.vital"), None)

    if base_path is None:
                                    #raise throws an exception which immediately stop the flow of the code
                                    # System Exit quits the program
        raise SystemExit("Save an Init preset in Vital as 'Sonora Base' first.")
    
    base = json.loads(base_path.read_text(encoding="utf-8"))
                                    # base_path.red_text(...) opens the preset file and reads it all as one long string of tezt
                                    # utf-8 tells Python how the charactesr are encoded so that symbols in preset names / comments read correctly
                                    # json.loads(...) turns this tezt into a python dict so we can access things like 'base["settings"]'

    OUT_DIR.mkdir(parents=True, exist_ok=True)
                                    # Creates "Documents\Vital\Sonora\Presets" if needed
                                    # parents = True creates any missing folders (Sonora / Presets)
                                    # exist_ok = True checks if the folder already exists and just moves on if it does.

    current_sound = None           
    while True:    # Whilst there is a 'description' this runs

        # Check if there's a current sound
        if current_sound is None:
            print("\nNo Current Sound.") 

            description = input("\nDescribe a sound (blank to quit):").strip()
            if not description:         # if there is no description ('blank to quit') then it stops
                break
            s = ask(description)        # ask(description) sends the text to the AI using the ask function and the stores the filled-in Sound in s.
            current_sound = s
            save_sound(s, base, description)
            
            modify_sound = input("\nModify current sound? (y/n)")
            if modify_sound.lower() == "n":
                current_sound = None
                description = False

        else: 
            print(f"\nCurrent Sound Name: {current_sound.name}")
            description = input("\nDescribe a change (blank to quit):").strip()
            if not description:         # if there is no description ('blank to quit') then it stops
                break
            tweak_description = f"""Using the following json attributes as the base for a synthesiser {current_sound.model_dump_json},
                                    apply the following changes {description}, keep all other values exactly the same."""
            tweaked_sound = ask(tweak_description)
            save_sound(tweaked_sound, base, description)

            current_sound = tweaked_sound

if __name__ == "__main__":
    main()