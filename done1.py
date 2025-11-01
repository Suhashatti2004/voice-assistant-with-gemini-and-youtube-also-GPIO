import os
import urllib.parse
import requests
import google.generativeai as genai
import speech_recognition as sr
from gtts import gTTS
from gpiozero import LED, Device
from gpiozero.pins.lgpio import LGPIOFactory
import threading
import time

# ---------------- GPIO SETUP ----------------
Device.pin_factory = LGPIOFactory()
LED_PIN = 17
led = LED(LED_PIN)
led.off()

# ---------------- GEMINI SETUP ----------------
genai.configure(api_key="gen-lang-client-0617628919")

# ---------------- SPEECH RECOGNITION SETUP ----------------
r = sr.Recognizer()

# ---------------- TEXT TO SPEECH ----------------
def speak(text):
    """Convert text to speech and play."""
    print("Assistant:", text)
    tts = gTTS(text=text, lang="en")
    tts.save("response.mp3")
    os.system("mpg321 response.mp3 >/dev/null 2>&1 &")

# ---------------- YOUTUBE FUNCTION ----------------
def play_youtube(song_name):
    try:
        speak(f"Playing {song_name} on YouTube.")
        query = urllib.parse.quote(song_name)
        html = requests.get(f"https://www.youtube.com/results?search_query={query}").text
        start = html.find("/watch?v=")
        if start != -1:
            video_id = html[start+9:start+20]
            url = f"https://www.youtube.com/watch?v={video_id}"
            print("🎵 Opening:", url)
            os.system(
                "chromium-browser --noerrdialogs --disable-infobars "
                "--autoplay-policy=no-user-gesture-required --start-fullscreen "
                f"'{url}' &"
            )
        else:
            speak("I couldn't find that song on YouTube.")
    except Exception as e:
        print("YouTube error:", e)
        speak("Sorry, I had trouble connecting to YouTube.")

def stop_youtube():
    speak("Stopping the song.")
    os.system("pkill chromium-browse >/dev/null 2>&1")
    os.system("pkill chromium >/dev/null 2>&1")

# ---------------- GEMINI FUNCTION ----------------
def ask_gemini(question):
    try:
        led.on()
        speak("Let me think...")
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(question)
        answer = response.text
    except Exception as e:
        print("Gemini Error:", e)
        answer = "Sorry, I couldn’t connect to Gemini right now."
    led.off()
    print("Gemini:", answer)
    speak(answer)

# ---------------- MAIN FUNCTION ----------------
def main():
    print("Available microphones:")
    for i, mic_name in enumerate(sr.Microphone.list_microphone_names()):
        print(f"{i}: {mic_name}")

    mic_index = int(input("Enter your Bluetooth mic index: "))

    with sr.Microphone(device_index=mic_index) as source:
        r.adjust_for_ambient_noise(source, duration=1)
        print("\n🎤 Voice assistant started.")
        print("Commands:\n - 'ask <question>' for Gemini\n - 'play <song>' for YouTube\n - 'light on/off' for LED\n - Combine commands like 'turn on light and play music'\n - Say 'quit' to exit.\n")

        led_state = False

        while True:
            print("Listening...")
            audio = r.listen(source, phrase_time_limit=5)

            try:
                command = r.recognize_google(audio).lower().strip()
                command = command.replace("turn on the", "light on").replace("turn off the", "light off")
                print("You said:", command)

                # ---------- EXIT ----------
                if "quit" in command or "exit" in command:
                    speak("Goodbye!")
                    stop_youtube()
                    break

                # ---------- MULTIPLE ACTION HANDLER ----------
                actions = []

                if "ask" in command:
                    actions.append("gemini")
                if "play" in command or "youtube" in command:
                    actions.append("youtube")
                if "stop" in command or "pause" in command:
                    actions.append("stop")
                if "light on" in command or "led on" in command or "switch on light" in command:
                    actions.append("light_on")
                if "light off" in command or "led off" in command or "switch off light" in command:
                    actions.append("light_off")

                # ---------- EXECUTE ACTIONS ----------
                if not actions:
                    # Default fallback: light control
                    if "on" in command:
                        led.on()
                        led_state = True
                        threading.Thread(target=speak, args=("Turning the light on.",)).start()
                    elif "off" in command:
                        led.off()
                        led_state = False
                        threading.Thread(target=speak, args=("Turning the light off.",)).start()
                    else:
                        speak("Please say ask, play, or light on or off.")
                else:
                    for act in actions:
                        if act == "gemini":
                            q = command.split("ask", 1)[-1].strip()
                            if q:
                                threading.Thread(target=ask_gemini, args=(q,)).start()
                            else:
                                speak("Please ask a complete question.")
                        elif act == "youtube":
                            song = command.replace("play", "").replace("youtube", "").strip()
                            threading.Thread(target=play_youtube, args=(song or "some music",)).start()
                        elif act == "stop":
                            threading.Thread(target=stop_youtube).start()
                        elif act == "light_on":
                            led.on()
                            led_state = True
                            threading.Thread(target=speak, args=("Turning the light on.",)).start()
                        elif act == "light_off":
                            led.off()
                            led_state = False
                            threading.Thread(target=speak, args=("Turning the light off.",)).start()

            except sr.UnknownValueError:
                print("Could not understand speech.")
            except sr.RequestError:
                print("Speech API connection issue.")
            except Exception as e:
                print("Error:", e)

            # Maintain LED state
            led.on() if led_state else led.off()
            time.sleep(0.2)

    print("Program stopped. LED stays in its last state.")

# ---------------- RUN ----------------
if __name__ == "__main__":
    main()
