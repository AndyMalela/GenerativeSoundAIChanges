from typing import Dict

from loguru import logger
from pyftg.models.attack_data import AttackData
from pyftg.models.enums.action import Action
from pyftg.models.enums.state import State
from pyftg.models.frame_data import CharacterData, FrameData
from pyftg_sound.models.audio_source import AudioSource
from pyftg_sound.sound_manager import SoundManager

from src.config import STAGE_HEIGHT, STAGE_WIDTH
from src.constants import source_attrs
from src.utils import is_guard


class CharacterAudioHandler:
    current_frame_number: int = 0
    temp: str = ' '
    temp2: str = ' '
    temp3: str = ' '
    pre_energy: int = 0
    previous_bottom: int = STAGE_HEIGHT
    previous_action: str = None
    heart_beat_flag: bool = False
    current_projectiles: Dict[str, AttackData] = {}

    player: bool
    character: CharacterData
    opp_character: CharacterData

    sound_manager: SoundManager
    source_default: AudioSource
    source_walking: AudioSource
    source_landing: AudioSource
    source_projectiles_by_id: Dict[str, AudioSource]
    source_energy_change: AudioSource
    source_border_alert: AudioSource
    source_border_alert_left: AudioSource
    source_heart_beat: AudioSource
    # source_projectile_hit: AudioSource

    def __init__(self, sound_manager: SoundManager, player: bool) -> None:
        self.sound_manager = sound_manager
        self.player = player
        self.source_default = self.sound_manager.create_audio_source(source_attrs)
        self.source_walking = self.sound_manager.create_audio_source(source_attrs)
        self.source_landing = self.sound_manager.create_audio_source(source_attrs)
        self.source_energy_change = self.sound_manager.create_audio_source(source_attrs)
        self.source_border_alert = self.sound_manager.create_audio_source(source_attrs)
        self.source_border_alert_left = self.sound_manager.create_audio_source(source_attrs)
        self.source_heart_beat = self.sound_manager.create_audio_source(source_attrs)
        self.source_beeping = self.sound_manager.create_audio_source(source_attrs)
        # self.source_projectile_hit = self.sound_manager.create_audio_source(source_attrs)

        self.current_projectiles = {}
        self.source_projectiles_by_id = {}
        
        self.previous_enemy_side = None
        self.source_side_alert = self.sound_manager.create_audio_source(source_attrs)
        
        self.source_timer_alert = self.sound_manager.create_audio_source(source_attrs)
        self.timer_alert_played = False

        # self.source_round_start = self.sound_manager.create_audio_source(source_attrs)
        # self.round_start_played = False
        
    # def check_round_start(self):
    #     if self.current_frame_number == 0 and not self.round_start_played:
    #         self.round_start_played = True
    #         self.sound_manager.play(
    #             self.source_round_start,
    #             self.sound_manager.get_sound_buffer("ROUNDSTART.wav"),
    #             0,
    #             0,
    #             False
    #         )
    #         logger.info(f"Play sound: RoundStart.wav on frame 0 ")

        
    def update_enemy_side_audio(self) -> None:
        if not self.player:  # Only run for Player 1 (or whichever you designate)
            return 
        if not hasattr(self, "character") or not hasattr(self, "opp_character"):
            return

        player_x = self.character.x
        enemy_x = self.opp_character.x

        current_side = "LEFT" if enemy_x < player_x else "RIGHT"

        if self.previous_enemy_side is None:
            self.previous_enemy_side = current_side  # Set without playing audio
        elif current_side != self.previous_enemy_side:
            sound_file = f"{current_side.upper()}.wav"
            self.sound_manager.play(
                self.source_side_alert,
                self.sound_manager.get_sound_buffer(sound_file),
                player_x,
                self.character.y,
                False 
            )
            logger.info(f"Enemy switched side to {current_side.upper()}, played {sound_file}")
            self.previous_enemy_side = current_side


    def check_timer_alert(self):
        total_match_frames = 60 * 60
        remaining_frames = total_match_frames - self.current_frame_number

        if remaining_frames <= 300 and not self.timer_alert_played: # 300 = 5 seconds * 60
            self.timer_alert_played = True
            alert_file = "5SECTIMED.wav"
            self.sound_manager.play(
                self.source_timer_alert,
                self.sound_manager.get_sound_buffer(alert_file),
                STAGE_WIDTH//2,
                0,
                False
            )
            logger.info(f"Play sound: {alert_file} at ({self.character.x}, {self.character.y}) on frame {self.current_frame_number}")
    
    def update_projectile(self):
        for projectile_id in self.source_projectiles_by_id:
            for _, proj in enumerate(self.character.projectile_attack):
                if not proj.empty_flag and proj.identifier == projectile_id:
                    x = (proj.current_hit_area.left + proj.current_hit_area.right) // 2
                    y = (proj.current_hit_area.top + proj.current_hit_area.bottom) // 2
                    self.sound_manager.set_source_pos(self.source_projectiles_by_id[projectile_id], x, y)
                    logger.info(f"Set source position: source_projectile on frame {self.current_frame_number} at ({x}, {y})")

        remove_projectiles = []
        for projectile_id in self.source_projectiles_by_id:
            if projectile_id not in [t.identifier for t in self.character.projectile_attack if not t.empty_flag]:
                self.sound_manager.stop(self.source_projectiles_by_id[projectile_id])
                logger.info(f"Stop source: source_projectile on frame {self.current_frame_number}")
                self.sound_manager.remove_source(self.source_projectiles_by_id[projectile_id])
                remove_projectiles.append(projectile_id)

        for projectile_id in remove_projectiles:
            del self.source_projectiles_by_id[projectile_id]
            del self.current_projectiles[projectile_id]

    def hit_attack(self, attack: AttackData, opponent: 'CharacterAudioHandler') -> None:
        if is_guard(self.character.action, attack):  # check guard
            self.sound_manager.play(self.source_landing, self.sound_manager.get_sound_buffer("WeakGuard.wav"), self.character.x, self.character.y, False)
            logger.info(f"Play sound: WeakGuard.wav on frame {self.current_frame_number} at ({self.character.x}, {self.character.y})")
        else:
            # check being hit
            if attack.attack_type == 4:
                if self.character.state not in [State.AIR, State.DOWN]:
                    self.run_action(Action.THROW_SUFFER)
                    if not self.opp_character.action is Action.THROW_SUFFER:
                        opponent.run_action(Action.THROW_HIT)
            else:
                if attack.down_prop:
                    self.sound_manager.play(self.source_landing, self.sound_manager.get_sound_buffer("HitB.wav"), self.character.x, self.character.y, False)
                    logger.info(f"Play sound: HitB.wav on frame {self.current_frame_number} at ({self.character.x}, {self.character.y})")
                else:
                    self.sound_manager.play(self.source_landing, self.sound_manager.get_sound_buffer("HitA.wav"), self.character.x, self.character.y, False)
                    logger.info(f"Play sound: HitA.wav on frame {self.current_frame_number} at ({self.character.x}, {self.character.y})")

    def run_action(self, action: Action) -> None:
        action_name = action.name.upper()
        sound_name = action_name + '.wav'

        x = self.character.x
        y = self.character.y

        if not hasattr(self, "previous_action_name"):
            self.previous_action_name = ""
            
        if action_name in ["STAND", "AIR"]:
            self.temp = ' '
            self.temp2 = ' '
            self.temp3 = ' '
        
        if action_name in ["JUMP", "FOR_JUMP", "BACK_JUMP", "THROW_A", "THROW_B", "THROW_HIT", "THROW_SUFFER", 
                      "STAND_A", "STAND_B", "CROUCH_A", "CROUCH_B", "AIR_A", "AIR_B", "AIR_DA", "AIR_DB", 
                      "STAND_FA", "STAND_FB", "CROUCH_FA", "CROUCH_FB", "AIR_FA", "AIR_FB", "AIR_UA", "AIR_UB", 
                      "STAND_F_D_DFA", "STAND_F_D_DFB", "STAND_D_DB_BA", "STAND_D_DB_BB", "AIR_F_D_DFA", 
                      "AIR_F_D_DFB", "AIR_D_DB_BA", "AIR_D_DB_BB"]:
            if sound_name != self.temp3:
                self.sound_manager.play(self.source_default, self.sound_manager.get_sound_buffer(sound_name), x, y, False)
                logger.info(f"Play sound: {sound_name} on frame {self.current_frame_number} at ({x}, {y})")
                self.temp3 = sound_name
        elif action_name == "CROUCH":
            self.temp3 = ' '
            if sound_name != self.temp:
                self.sound_manager.play(self.source_default, self.sound_manager.get_sound_buffer(sound_name), x, y, False)
                logger.info(f"Play sound: {sound_name} on frame {self.current_frame_number} at ({x}, {y})")
                self.temp = sound_name
        elif action_name in ["FORWARD_WALK", "DASH", "BACK_STEP"]:
            if sound_name != self.temp2:
                self.sound_manager.play(self.source_walking, self.sound_manager.get_sound_buffer(sound_name), x, y, True)
                logger.info(f"Play sound: {sound_name} on frame {self.current_frame_number} at ({x}, {y})")
                self.temp2 = sound_name
        elif action_name in ["STAND_D_DF_FA", "STAND_D_DF_FB", "AIR_D_DF_FA", "AIR_D_DF_FB", "STAND_D_DF_FC"]:
            if sound_name == self.temp3:
                return
            for i, proj in enumerate(self.character.projectile_attack):
                if not proj.empty_flag:
                    projectile_id = proj.identifier
                    if projectile_id not in self.current_projectiles.keys():
                        self.current_projectiles[projectile_id] = proj
                        projectile_source = self.sound_manager.create_audio_source(source_attrs)
                        self.source_projectiles_by_id[projectile_id] = projectile_source
                        self.sound_manager.play(projectile_source, self.sound_manager.get_sound_buffer(sound_name), x, y, True)
                        logger.info(f"Play sound: {sound_name} on frame {self.current_frame_number} at ({x}, {y})")
                        self.temp3 = sound_name
                        break
                    
    # def check_projectile_collision(self):
        
    #     for proj in self.character.projectile_attack:
    #         if not proj.empty_flag:
    #             # AABB collision with opp_character
    #             if (proj.current_hit_area.left < self.opp_character.right and
    #                 proj.current_hit_area.right > self.opp_character.left and
    #                 proj.current_hit_area.top < self.opp_character.bottom and
    #                 proj.current_hit_area.bottom > self.opp_character.top):

    #                 # Mark projectile as used
    #                 proj.empty_flag = True

    #                 # Play hit sound
    #                 buffer = self.sound_manager.get_sound_buffer("MaleFire_Hit.wav")
    #                 if buffer is not None:
    #                     hit_x = (proj.current_hit_area.left + proj.current_hit_area.right) // 2
    #                     hit_y = (proj.current_hit_area.top + proj.current_hit_area.bottom) // 2
    #                     self.sound_manager.play(
    #                         self.source_projectile_hit,  # Initialize this in __init__!
    #                         buffer,
    #                         self.opp_character.x, self.opp_character.y, False
    #                     )
    #                 else:
    #                     print("ERROR: MaleFire_Hit.wav sound buffer not loaded!")
    #                 logger.info(
    #                     f"MaleFire_Hit.wav played on projectile hit at frame {self.current_frame_number} at "
    #                     f"({self.opp_character.x}, {self.opp_character.y})"
    #                 )
    
    def check_landing(self):
        if self.character.bottom >= STAGE_HEIGHT and self.character.bottom != self.previous_bottom:
            self.sound_manager.play(self.source_landing, self.sound_manager.get_sound_buffer("LANDING.wav"), self.character.x, self.character.y, False)
            logger.info(f"Play sound: LANDING.wav on frame {self.current_frame_number} at ({self.character.x}, {self.character.y})")
        self.previous_bottom = self.character.bottom

    def check_border_alert(self):
        if not self.player:  # Only run for Player 1 (or whichever you designate)
            return 
        if not hasattr(self, "character") or not hasattr(self, "opp_character"):
            return
        
        if (self.character.left == 0 and self.character.speed_x < 0):
            if not self.sound_manager.is_playing(self.source_border_alert_left):
                self.sound_manager.play(
                    self.source_border_alert_left,
                    self.sound_manager.get_sound_buffer("Border_Alert.wav"),
                    0, 0, False
                )
                logger.info(f"Play sound: Border_Alert.wav on frame {self.current_frame_number} at (0, 0)")

        elif (self.character.right == STAGE_WIDTH and self.character.speed_x > 0):
            if not self.sound_manager.is_playing(self.source_border_alert):
                self.sound_manager.play(
                    self.source_border_alert,
                    self.sound_manager.get_sound_buffer("BorderAlert.wav"),
                    STAGE_WIDTH, 0, False
                )
                logger.info(f"Play sound: BorderAlert.wav on frame {self.current_frame_number} at ({STAGE_WIDTH}, 0)")
    

    def check_heart_beat(self):
        if not self.player:  # Only run for Player 1 (or whichever you designate)
            return 
        if not hasattr(self, "character") or not hasattr(self, "opp_character"):
            return
    
    
        hp = self.character.hp
        position_x = 0 if self.player else STAGE_WIDTH

        # --- Below 50: Only Beeping ---
        if hp < 50:
            # Stop heartbeat if playing
            if self.sound_manager.is_playing(self.source_heart_beat):
                self.sound_manager.stop(self.source_heart_beat)
                logger.info(f"Stop heartbeat at HP={hp}, frame={self.current_frame_number}")

            # Start beeping if not already playing
            if not self.sound_manager.is_playing(self.source_beeping):
                self.sound_manager.set_source_gain(self.source_beeping, 0.5)
                self.sound_manager.play(
                    self.source_beeping,
                    self.sound_manager.get_sound_buffer("Beep.wav"),
                    STAGE_WIDTH//2,
                    0,
                    True  # Loop enabled
                )
                logger.info(f"Start looping beeping at HP={hp}, frame={self.current_frame_number}")
        # --- 50 <= HP < 200: Only Heartbeat ---
        elif hp < 200:
            # Stop beeping if playing
            if self.sound_manager.is_playing(self.source_beeping):
                self.sound_manager.stop(self.source_beeping)
                logger.info(f"Stop beeping at HP={hp}, frame={self.current_frame_number}")

            # Start heartbeat if not already playing
            if not self.sound_manager.is_playing(self.source_heart_beat):
                self.sound_manager.set_source_gain(self.source_heart_beat, 3.0)
                self.sound_manager.play(
                    self.source_heart_beat,
                    self.sound_manager.get_sound_buffer("Heartbeat.wav"),
                    STAGE_WIDTH//2,
                    0,
                    True  # Loop enabled
                )
                logger.info(f"Start looping heartbeat at HP={hp}, frame={self.current_frame_number}")
        # --- HP >= 200: Stop All ---
        else:
            if self.sound_manager.is_playing(self.source_heart_beat):
                self.sound_manager.stop(self.source_heart_beat)
                logger.info(f"Stop heartbeat at HP={hp}, frame={self.current_frame_number}")
            if self.sound_manager.is_playing(self.source_beeping):
                self.sound_manager.stop(self.source_beeping)
                logger.info(f"Stop beeping at HP={hp}, frame={self.current_frame_number}")


    def check_energy_charge(self):
        if self.character.energy > self.pre_energy + 50:
            self.pre_energy = self.character.energy
            if self.player:
                self.sound_manager.play(self.source_energy_change, self.sound_manager.get_sound_buffer("EnergyCharge.wav"), 0, 0, False)
                logger.info(f"Play sound: EnergyCharge.wav on frame {self.current_frame_number} at (0, 0)")
            else:
                self.sound_manager.play(self.source_energy_change, self.sound_manager.get_sound_buffer("EnergyCharge.wav"), STAGE_WIDTH, 0, False)
                logger.info(f"Play sound: EnergyCharge.wav on frame {self.current_frame_number} at ({STAGE_WIDTH}, 0)")
    
    def update(self, frame_data: FrameData):
        self.current_frame_number = frame_data.current_frame_number
        self.character = frame_data.get_character(self.player)
        self.opp_character = frame_data.get_character(not self.player)

        self.check_landing()
        self.check_border_alert()
        self.check_heart_beat()
        self.check_energy_charge()
        self.update_enemy_side_audio()
        self.check_timer_alert()
        # self.check_round_start()
        # self.check_projectile_collision()


        if not self.character.state is State.CROUCH:
            self.temp = " "
        if self.character.speed_x == 0 or self.character.state is State.AIR:
            self.temp2 = " "
            if self.sound_manager.is_playing(self.source_walking):
                self.sound_manager.stop(self.source_walking)
                logger.info(f"Stop source: source_walking on frame {self.current_frame_number}")
        else:
            self.sound_manager.set_source_pos(self.source_walking, self.character.x, self.character.y)
            logger.info(f"Set source position: source_walking on frame {self.current_frame_number} at ({self.character.x}, {self.character.y})")

        self.run_action(self.character.action)
        #self.run_action(self.opp_character.action)
        self.update_projectile()

    def reset(self) -> None:
        self.pre_energy = 0
        self.temp = ' '
        self.temp2 = ' '
        self.temp3 = ' '
        self.previous_bottom = STAGE_HEIGHT
        self.heart_beat_flag = False
        self.current_projectiles = {}
        self.previous_enemy_side = None
        self.timer_alert_played = False
        # self.round_start_played = False
        for source in self.source_projectiles_by_id.values():
            self.sound_manager.stop(source)
            self.sound_manager.remove_source(source)
        self.source_projectiles_by_id = {}
        logger.info("Reset character data")
    