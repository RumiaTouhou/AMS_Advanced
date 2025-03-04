import pygame
import math
import sys
import random
from pygame.locals import *
from enum import Enum

pygame.init()

class GameState(Enum):
    NOT_STARTED = 0
    RUNNING = 1
    PAUSED = 2
    GAME_OVER = 3

MAX_TILT = 45  
TILT_BEGINNING = 5  

PLATE_RADIUS = 1000
BALL_RADIUS = 30

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
FPS = 60

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

TILT_RATE = 0.48 

INITIAL_ROLLING_RESISTANCE = 0.18
MIN_ROLLING_RESISTANCE = 0.01
RESISTANCE_CHANGE_START_TIME = 20 
RESISTANCE_CHANGE_INTERVAL = 6    
RESISTANCE_CHANGE_STEP = 0.01    

INITIAL_GRAVITY = 0.08
MAX_GRAVITY = 0.16
GRAVITY_CHANGE_START_TIME = 110    
GRAVITY_CHANGE_INTERVAL = 20      
GRAVITY_CHANGE_STEP = 0.01       

INITIAL_MAX_SPEED = 6.0
ABSOLUTE_MAX_SPEED = 14.0
SPEED_CHANGE_START_TIME = 230     
SPEED_CHANGE_INTERVAL = 20        
SPEED_CHANGE_STEP = 0.5          

DISPLAY_SCALE = 0.27

STATUS_FONT_SIZE = 32  
MESSAGE_FONT_SIZE = 64 

class Ball:
    def __init__(self, x, y):
        self.reset(x, y)
    
    def reset(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.ax = 0
        self.ay = 0
        

    def update(self, plate, current_gravity, current_rolling_resistance, current_max_speed):
        angle_rad = math.radians(plate.tilt_magnitude)
        direction_rad = math.radians(plate.tilt_direction)
        
        sliding_force = current_gravity * math.sin(angle_rad)
        sliding_ax = sliding_force * math.cos(direction_rad)
        sliding_ay = sliding_force * math.sin(direction_rad)
        
        normal_force = current_gravity * math.cos(angle_rad)
        
        speed = math.sqrt(self.vx*self.vx + self.vy*self.vy)
        
        self.ax = sliding_ax
        self.ay = sliding_ay
        
        if speed > 0:
            resistance_force = current_rolling_resistance * normal_force
            
            resistance_ax = -resistance_force * (self.vx / speed)
            resistance_ay = -resistance_force * (self.vy / speed)
            
            self.ax += resistance_ax
            self.ay += resistance_ay
        
        self.vx += self.ax
        self.vy += self.ay
        
        new_speed = math.sqrt(self.vx*self.vx + self.vy*self.vy)
        
        if plate.tilt_magnitude > 0.5: 
            min_speed = plate.tilt_magnitude * 0.015
            
            if 0 < new_speed < min_speed:
                scale_factor = min_speed / new_speed
                self.vx *= scale_factor
                self.vy *= scale_factor
        
        new_speed = math.sqrt(self.vx*self.vx + self.vy*self.vy)
        if new_speed > current_max_speed:
            scale = current_max_speed / new_speed
            self.vx *= scale
            self.vy *= scale
        
        self.x += self.vx
        self.y += self.vy
        
        distance = math.sqrt(self.x*self.x + self.y*self.y)
        if distance > PLATE_RADIUS - BALL_RADIUS:
            return False
        
        return True

    def get_speed(self):
        return math.sqrt(self.vx * self.vx + self.vy * self.vy)

    def get_distance_from_center(self):
        return math.sqrt(self.x * self.x + self.y * self.y)

    def get_distance_to_edge(self):
        return PLATE_RADIUS - self.get_distance_from_center() - BALL_RADIUS

class Plate:
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.tilt_magnitude = 0  
        self.tilt_direction = 0 
        self.x_tilt = 0 
        self.y_tilt = 0 
        
    def apply_random_tilt(self):
        random_direction = random.randint(0, 359)
        self.tilt_magnitude = TILT_BEGINNING
        self.tilt_direction = random_direction
        
        direction_rad = math.radians(self.tilt_direction)
        self.x_tilt = self.tilt_magnitude * math.cos(direction_rad)
        self.y_tilt = self.tilt_magnitude * math.sin(direction_rad)
        
    def update(self, keys):
        if keys[K_w]: self.y_tilt -= TILT_RATE
        if keys[K_s]: self.y_tilt += TILT_RATE
        if keys[K_a]: self.x_tilt -= TILT_RATE
        if keys[K_d]: self.x_tilt += TILT_RATE
        
        magnitude = math.sqrt(self.x_tilt * self.x_tilt + self.y_tilt * self.y_tilt)
        
        if magnitude > 0:
            if magnitude > MAX_TILT:
                scale = MAX_TILT / magnitude
                self.x_tilt *= scale
                self.y_tilt *= scale
                magnitude = MAX_TILT
            
            self.tilt_magnitude = magnitude
            self.tilt_direction = math.degrees(math.atan2(self.y_tilt, self.x_tilt))
            if self.tilt_direction < 0:
                self.tilt_direction += 360

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Balance Ball Game")
        self.clock = pygame.time.Clock()
        
        self.plate = Plate()
        self.ball = Ball(0, 0)  
        self.state = GameState.NOT_STARTED
        
        self.center_x = WINDOW_WIDTH // 2
        self.center_y = WINDOW_HEIGHT // 2
        
        self.font = pygame.font.Font(None, STATUS_FONT_SIZE)
        self.large_font = pygame.font.Font(None, MESSAGE_FONT_SIZE)
        
        self.game_time = 0  
        self.current_gravity = INITIAL_GRAVITY
        self.current_rolling_resistance = INITIAL_ROLLING_RESISTANCE
        self.current_max_speed = INITIAL_MAX_SPEED
        
    def reset(self):
        self.plate.reset()
        self.ball.reset(0, 0)
        self.state = GameState.NOT_STARTED
        
        self.game_time = 0
        self.current_gravity = INITIAL_GRAVITY
        self.current_rolling_resistance = INITIAL_ROLLING_RESISTANCE
        self.current_max_speed = INITIAL_MAX_SPEED

    def update_difficulty(self):
        if self.game_time >= RESISTANCE_CHANGE_START_TIME:
            changes = (self.game_time - RESISTANCE_CHANGE_START_TIME) // RESISTANCE_CHANGE_INTERVAL
            new_resistance = max(
                MIN_ROLLING_RESISTANCE,
                INITIAL_ROLLING_RESISTANCE - (changes * RESISTANCE_CHANGE_STEP)
            )
            self.current_rolling_resistance = new_resistance
            
        if self.game_time >= GRAVITY_CHANGE_START_TIME:
            changes = (self.game_time - GRAVITY_CHANGE_START_TIME) // GRAVITY_CHANGE_INTERVAL
            new_gravity = min(
                MAX_GRAVITY,
                INITIAL_GRAVITY + (changes * GRAVITY_CHANGE_STEP)
            )
            self.current_gravity = new_gravity
            
        if self.game_time >= SPEED_CHANGE_START_TIME:
            changes = (self.game_time - SPEED_CHANGE_START_TIME) // SPEED_CHANGE_INTERVAL
            new_max_speed = min(
                ABSOLUTE_MAX_SPEED,
                INITIAL_MAX_SPEED + (changes * SPEED_CHANGE_STEP)
            )
            self.current_max_speed = new_max_speed

    def get_display_angle(self, actual_angle):
        return (actual_angle + 90) % 360
        
    def draw(self):
        self.screen.fill(BLACK)
        
        pygame.draw.circle(self.screen, WHITE, 
                           (self.center_x, self.center_y), 
                           int(PLATE_RADIUS * DISPLAY_SCALE), 
                           2)
        
        reference_angles = [15, 30, 45]
        for angle in reference_angles:
            radius = PLATE_RADIUS * (angle / MAX_TILT)
            draw_radius = int(radius * DISPLAY_SCALE)
            pygame.draw.circle(self.screen, GREEN, (self.center_x, self.center_y), draw_radius, 1)
            
            label = f"{angle}°"
            text_x = self.center_x + int(draw_radius * math.cos(math.pi / 4))
            text_y = self.center_y - int(draw_radius * math.sin(math.pi / 4))
            
            text_surface = self.font.render(label, True, GREEN)
            self.screen.blit(text_surface, (text_x, text_y))
        
        for angle in range(0, 360, 90):
            end_x = self.center_x + int(PLATE_RADIUS * math.cos(math.radians(angle)) * DISPLAY_SCALE)
            end_y = self.center_y + int(PLATE_RADIUS * math.sin(math.radians(angle)) * DISPLAY_SCALE)
            pygame.draw.line(self.screen, GREEN, (self.center_x, self.center_y), (end_x, end_y), 1)
        
        label_distance = (PLATE_RADIUS + 30) * DISPLAY_SCALE
        labels = {
            'W': (self.center_x, self.center_y - label_distance),
            'S': (self.center_x, self.center_y + label_distance),
            'A': (self.center_x - label_distance, self.center_y),
            'D': (self.center_x + label_distance, self.center_y)
        }
        for text, pos in labels.items():
            surface = self.font.render(text, True, WHITE)
            rect = surface.get_rect(center=(int(pos[0]), int(pos[1])))
            self.screen.blit(surface, rect)
        
        if self.plate.tilt_magnitude > 0:
            arrow_length = PLATE_RADIUS * (self.plate.tilt_magnitude / MAX_TILT)
            arrow_length *= DISPLAY_SCALE
            
            angle_rad = math.radians(self.plate.tilt_direction)
            end_x = self.center_x + arrow_length * math.cos(angle_rad)
            end_y = self.center_y + arrow_length * math.sin(angle_rad)
            
            pygame.draw.line(self.screen, YELLOW, 
                             (self.center_x, self.center_y), 
                             (end_x, end_y), 3)
            
            head_length = 15 
            head_angle = math.pi / 6
            
            for offset in [-head_angle, head_angle]:
                head_x = end_x - head_length * math.cos(angle_rad + offset)
                head_y = end_y - head_length * math.sin(angle_rad + offset)
                pygame.draw.line(self.screen, YELLOW,
                                 (end_x, end_y),
                                 (head_x, head_y), 3)
        
        ball_screen_x = self.center_x + int(self.ball.x * DISPLAY_SCALE)
        ball_screen_y = self.center_y + int(self.ball.y * DISPLAY_SCALE)
        pygame.draw.circle(self.screen, RED, 
                           (ball_screen_x, ball_screen_y), 
                           int(BALL_RADIUS * DISPLAY_SCALE))
        
        status_text = [
            f"Plate tilt magnitude: {self.plate.tilt_magnitude:.1f}°",
            f"Plate tilt direction: {self.get_display_angle(self.plate.tilt_direction):.1f}°",
            f"Distance from center: {self.ball.get_distance_from_center():.1f}px",
            f"Distance to edge: {self.ball.get_distance_to_edge():.1f}px",
            f"Ball speed: {self.ball.get_speed():.1f}px/frame"
        ]
        
        if self.state == GameState.RUNNING or self.state == GameState.PAUSED:
            status_text.append(f"Game time: {self.game_time:.1f}s")
        
        y_offset = 20
        for text_line in status_text:
            surface = self.font.render(text_line, True, WHITE)
            self.screen.blit(surface, (WINDOW_WIDTH - 400, y_offset))
            y_offset += 30

        if self.state == GameState.NOT_STARTED:
            text = self.large_font.render("Press SPACE to Start", True, WHITE)
            text_rect = text.get_rect(center=(self.center_x, self.center_y))
            self.screen.blit(text, text_rect)
        elif self.state == GameState.PAUSED:
            text = self.large_font.render("PAUSED", True, WHITE)
            text_rect = text.get_rect(center=(self.center_x, self.center_y))
            self.screen.blit(text, text_rect)
        elif self.state == GameState.GAME_OVER:
            text = self.large_font.render("Game Over. Press R to Restart", True, RED)
            text_rect = text.get_rect(center=(self.center_x, self.center_y))
            self.screen.blit(text, text_rect)
        
        pygame.display.flip()
        
    def run(self):
        prev_time = pygame.time.get_ticks()
        
        while True:
            current_time = pygame.time.get_ticks()
            dt = (current_time - prev_time) / 1000.0  
            prev_time = current_time
            
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == KEYDOWN:
                    if event.key == K_SPACE:
                        if self.state == GameState.NOT_STARTED:
                            self.state = GameState.RUNNING
                            self.plate.apply_random_tilt()
                        elif self.state == GameState.RUNNING:
                            self.state = GameState.PAUSED
                        elif self.state == GameState.PAUSED:
                            self.state = GameState.RUNNING
                    elif event.key == K_r and self.state == GameState.GAME_OVER:
                        self.reset()
            
            keys = pygame.key.get_pressed()
            
            if self.state == GameState.RUNNING:
                self.game_time += dt
                
                self.update_difficulty()
                
                self.plate.update(keys)
                if not self.ball.update(self.plate, self.current_gravity, 
                                      self.current_rolling_resistance, 
                                      self.current_max_speed):
                    self.state = GameState.GAME_OVER
            
            self.draw()
            self.clock.tick(FPS)

if __name__ == "__main__":
    game = Game()
    game.run()