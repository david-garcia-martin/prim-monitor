import pyautogui
import random
import time

def random_move_and_click():
    # Set the screen resolution (adjust according to your screen)
    screen_width, screen_height = pyautogui.size()

    while True:
        # Generate random coordinates within the screen boundaries
        x = random.randint(0, screen_width - 1)
        y = random.randint(0, screen_height - 1)

        # Move the cursor to the random coordinate
        pyautogui.moveTo(x, y, duration=0.5)

        # Click at the specific area (adjust coordinates according to your needs)
        pyautogui.click(x=100, y=100)

        # Wait for 10 seconds before the next iteration
        time.sleep(10)

if __name__ == "__main__":
    random_move_and_click()
