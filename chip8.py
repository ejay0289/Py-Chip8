import random
import sys
import pygame
import winsound




class Register:
    def __init__(self,bits):
        self.value = 0
        self.bits = bits

    def checkCarry(self):
        # Check if the register exceeds the number of bits allowed
        if self.value > (1 << self.bits) - 1:
            self.value &= (1 << self.bits) - 1  # Mask to keep within the register's bit limit
            return 1  # Carry
        return 0
    
    def checkBorrow(self):
        if self.value < 0:
            self.value = abs(self.value)
            return 0
        
        return 1
    

class DelayTimer:
    def __init__(self):
        self.timer = 0
    
    def countDown(self):
        if self.timer > 0:
            self.timer -= 1

    def setTimer(self, value):
        self.timer = value
    
    def readTimer(self):
        return self.timer
    
class SoundTimer(DelayTimer):
    def __init__(self):
        DelayTimer.__init__(self)

    def beep(self):
        if self.timer > 1:
            # Play a simple beep sound (frequency 440 Hz for 500 ms)
            frequency = 440  # Hertz (A4 note)
            duration = 500   # Duration in milliseconds
            winsound.Beep(frequency, duration)
            self.timer = 0

class Chip8:


    def __init__(self):
        self.memory = [0] * 4096

        fonts = [	
    0xF0, 0x90, 0x90, 0x90, 0xF0, #// 0
	0x20, 0x60, 0x20, 0x20, 0x70, #// 1
	0xF0, 0x10, 0xF0, 0x80, 0xF0, #// 2
	0xF0, 0x10, 0xF0, 0x10, 0xF0, #// 3
	0x90, 0x90, 0xF0, 0x10, 0x10, #// 4
	0xF0, 0x80, 0xF0, 0x10, 0xF0, #// 5
	0xF0, 0x80, 0xF0, 0x90, 0xF0, #// 6
	0xF0, 0x10, 0x20, 0x40, 0x40, #// 7
	0xF0, 0x90, 0xF0, 0x90, 0xF0, #// 8
	0xF0, 0x90, 0xF0, 0x10, 0xF0, #// 9
	0xF0, 0x90, 0xF0, 0x90, 0x90, #// A
	0xE0, 0x90, 0xE0, 0x90, 0xE0, #// B
	0xF0, 0x80, 0x80, 0x80, 0xF0, #// C
	0xE0, 0x90, 0x90, 0x90, 0xE0, #// D
	0xF0, 0x80, 0xF0, 0x80, 0xF0, #// E
	0xF0, 0x80, 0xF0, 0x80, 0x80  #// F
        ]
        for i in range(len(fonts)):
            self.memory[i] = fonts[i]


        self.registers_v = [Register(8) for _ in range(16)]
        self.index_register = 0
        self.PC = 0x200
        
        self.stack = []

        self.delay_timer = DelayTimer()
        self.sound_timer = SoundTimer()
        pygame.init()
        pygame.time.set_timer(pygame.USEREVENT+1, int(1000 / 60))
        pygame.display.set_caption("Chip8 by ejay")

        self.keys = [False] *16
        

        self.keypad = {
            49 : 1,
            50 : 2,
            51 : 3,
            52 : 0xc,
            113 : 4,
            119 : 5,
            101 : 6,
            114 : 0xd,
            97 : 7,
            115 : 8,
            100 : 9,
            102 : 0xe,
            122 : 0xa,
            120 : 0,
            99 : 0xb,
            118 : 0xf
        }
        
        

        self.grid = []
        for i in range(32):
            line=[]
            for j in range(64):
                line.append(0)
            self.grid.append(line)

        self.empty_grid = self.grid[:]
        self.zero_color = [0,0,0]
        self.one_color = [255,255,255]

        self.screen_multiplier = 10
        width = 64
        height = 32
        self.screen = pygame.display.set_mode([width * self.screen_multiplier, height * self.screen_multiplier])

        self.screen.fill(self.one_color)
        pygame.display.flip()





    def readProg(self, filename):
        rom = self.convertProg(filename)
        
        offset = int('0x200', 16)
        for i in rom:
            self.memory[offset] = i
            offset += 1

        # for byte in rom:
        #     print(hex(byte)[2:].zfill(2),end='')
    
    def convertProg(self, filename):
        rom = []

        with open(filename, 'rb') as f:
            wholeProgram = f.read()

            for i in wholeProgram:
                opcode = i
                rom.append(opcode)
        
        return rom

    def clear(self):
        for i in range(len(self.grid)):
            for j in range(len(self.grid[0])):
                self.grid[i][j] = 0



    def execute_opcode(self,opcode):
        # Extract x, y, and other parts of the opcode directly
        x = int(opcode[1], 16)  # Vx (second character)
        y = int(opcode[2], 16)  # Vy (third character)

        
        if opcode[0]=='0':
            # 1. 00E0 - Clear the screen
            if opcode == "00e0":
                self.clear()
            # 2. 00EE - Return from subroutine
            elif opcode == "00ee":
                self.PC = self.stack.pop()
        # 3. 1NNN - Jump to address NNN
        elif opcode[0] == '1':
            self.PC = int(opcode[1:],16)-2

        # 4. 2NNN - Call subroutine at address NNN
        elif opcode[0] == '2':
            self.stack.append(self.PC)
            self.PC = int(opcode[1:],16) - 2

        # 5. 3XNN - Skip next instruction if Vx == NN
        elif opcode[0] == '3':
            byte = int(opcode[2:],16)

            if self.registers_v[x].value == byte:
                self.PC += 2

        # 6. 4XNN - Skip next instruction if Vx != NN
        elif opcode[0] == "4":
            byte = int(opcode[2:],16)

            if self.registers_v[x].value != byte:
                self.PC += 2

        # 7. 5XY0 - Skip next instruction if Vx == Vy
        if opcode[0] == "5" and opcode[3] == "0":
            if self.registers_v[x].value == self.registers_v[y].value:
                self.PC += 2

        # 8. 6XNN - Load NN into Vx
        if opcode[0] == '6':
            self.registers_v[x].value = int(opcode[2:],16)

        # 9. 7XNN - Add NN to Vx
        if opcode[0] == '7':
            self.registers_v[x].value += int(opcode[2:],16) 
            self.registers_v[x].checkCarry()

        if opcode[0] == '8':
          # 10. 8XY0 - Load Vy into Vx
            if opcode[3] == '0':
                self.registers_v[x].value = self.registers_v[y].value

            # 11. 8XY1 - Vx = Vx OR Vy
            elif opcode[3] == '1':
                self.registers_v[x].value = self.registers_v[x].value | self.registers_v[y].value


        # 12. 8XY2 - Vx = Vx AND Vy    
            elif opcode[3] == '2':
                self.registers_v[x].value = self.registers_v[x].value & self.registers_v[y].value

        # 13. 8XY3 - Vx = Vx XOR Vy
            elif opcode[3] == '3':
                self.registers_v[x].value = self.registers_v[x].value ^ self.registers_v[y].value
        
        # 14. 8XY4 - Add Vy to Vx and set VF
            elif opcode[3] == '4':
                self.registers_v[x].value += self.registers_v[y].value
                self.registers_v[0xf].value = self.registers_v[x].checkCarry()

        # 15. 8XY5 - Subtract Vy from Vx and set VF

            elif opcode[3] == '5':
                self.registers_v[x].value -= self.registers_v[y].value
                self.registers_v[0xF].value = self.registers_v[x].checkBorrow()
                 

        # 16. 8XY6 - Shift Vx right by 1
            elif opcode[3] == '6':
                least_bit = self.registers_v[x].value & 1
                self.registers_v[x].value >>= 1
                self.registers_v[0xF].value =least_bit

        # 17. 8XY7 - Subtract Vx from Vy and set VF
            elif opcode[3] == '7':
                self.registers_v[x].value = self.registers_v[y].value - self.registers_v[x].value
                self.registers_v[0xF].value = self.registers_v[x].checkBorrow()

        # 18. 8XYE - Shift Vx left by 1
            elif opcode[3] == 'e':
                msb = (self.registers_v[x].value >> 7) & 1

                self.registers_v[0xF].value = msb
                self.registers_v[x].value <<= 1


    # 19. 9XY0 - Skip next instruction if Vx != Vy
        if opcode[0] == '9':
            if self.registers_v[x].value != self.registers_v[y].value:
                self.PC += 2


        # 20. ANNN - Load address NNN into I
        if opcode[0] == 'a':
            self.index_register = int(opcode[1:],16)
        
        # 21. BNNN - Jump to address NNN + V0
        if opcode[0] == 'b':
            self.PC = (int(opcode[1:],16) + self.registers_v[0x0].value) - 2

        # 22. CXNN - Set Vx to a random byte AND NN
        if opcode[0] == 'c':
            random_byte = random.randint(0,255)
            instruction_byte = int(opcode[2:],16)
            self.registers_v[x].value = instruction_byte & random_byte 

        # 23. DXYN - Draw sprite at Vx, Vy with n bytes of sprite data
        if opcode[0] == 'd':

            n = int(opcode[3],16)
            addr = self.index_register
            sprite = self.memory[addr: addr+n]

            for i in range(len(sprite)):
                if type(sprite[i]) == str:
                     sprite[i] = int(sprite[i], 16)


            if self.draw(self.registers_v[x].value, self.registers_v[y].value, sprite):
                self.registers_v[0xf].value = 1
            else:
                self.registers_v[0xf].value = 0


        elif opcode[0] == 'e':
    # 24. EX9E - Skip next instruction if key with value Vx is pressed
            if opcode[2:] == '9e':
                key = self.registers_v[x].value
                if self.keys[key]:
                    self.PC += 2
        # 25. EXA1 - Skip next instruction if key with value Vx is not pressed
            elif opcode[2:] == 'a1':
                key = self.registers_v[x].value
                if not self.keys[key]:
                    self.PC += 2

        elif opcode[0] == 'f':
        # 26. FX07 - Set Vx to the value of the delay timer
            if opcode[2:] == '07':
                self.registers_v[x].value = self.delay_timer.readTimer()
            
            # 27. FX0A - Wait for a key press, store the value in Vx
            elif opcode[2:] == '0a':
                key = None

                while True:
                    self.key_press()
                    isKeyDown = False

                    for i in range(len(self.keys)):
                        if self.keys[i]:
                            key = i
                            isKeyDown = True
                    
                    if isKeyDown:
                        break
                
                self.registers_v[x].value = key
        # 28. FX15 - Set the delay timer to Vx

            elif opcode[2:] == '15':
                self.delay_timer.setTimer(self.registers_v[x].value)

        # 29. FX18 - Set the sound timer to Vx
            elif opcode[2:] == '18':
                self.sound_timer.setTimer(self.registers_v[x].value)

        # 30. FX1E - Add Vx to I

            elif opcode[2:] == '1e':
                self.index_register += self.registers_v[x].value

        #31 FX29 - 
            elif opcode[2:] == '29':
                self.index_register = self.registers_v[x].value * 5



            elif opcode[2:] == '33':
                value = str(self.registers_v[x].value)
                fillNum = 3 - len(value)
                value = '0' * fillNum + value
                for i in range(len(value)):
                    self.memory[self.index_register + i] = int(value[i])

            elif opcode[2:] == '55':
                #Store V0 to Vx in memory starting from I
                #v0 -v5
                for i in range(0,x+1):
                    self.memory[self.index_register + i] = self.registers_v[i].value

            elif opcode[2:] == '65':
                #read v0 - Vx from memory
                for i in range(0, x+1):
                    self.registers_v[i].value = self.memory[self.index_register + i] 
                
        self.PC += 2

    def key_press(self):

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

            if event.type == pygame.USEREVENT+1:
                self.delay_timer.countDown()


            if event.type == pygame.KEYDOWN:
                try:
                    target_key = self.keypad[event.key]
                    self.keys[target_key] = True
                except:pass

            if event.type == pygame.KEYUP:
                try:
                    target_key = self.keypad[event.key]
                    self.keys[target_key] = False
                except: pass

            keys = pygame.key.get_pressed()

            if keys[pygame.K_ESCAPE]:
                pygame.quit()
                sys.exit()

            


    def draw(self, Vx, Vy, sprite):
        collision = False

        spriteBits = []
        for i in sprite:
            binary = bin(i)
            line = list(binary[2:])
            fillNum = 8 - len(line)
            line = ['0'] * fillNum + line

            spriteBits.append(line)
        
        '''
        for i in spriteBits:
            print(i)
        '''

        for i in range(len(spriteBits)):
            #line = ''
            for j in range(8):
                try:
                    if self.grid[Vy + i][Vx + j] == 1 and int(spriteBits[i][j]) == 1:
                        collision = True

                    self.grid[Vy + i][Vx + j] = self.grid[Vy + i][Vx + j] ^ int(spriteBits[i][j])
                    #line += str(int(spriteBits[i][j]))
                except:
                    continue

            #print(line)
        
        return collision
        

    def hex_to_opcode(self,hexvalue):
        opcode = hex(hexvalue)[2:].zfill(2)
        return opcode

    def cycle(self):
        index = self.PC

        high_bit = self.hex_to_opcode(self.memory[index])
        low_bit = self.hex_to_opcode(self.memory[index+1])
        opcode = high_bit + low_bit
        self.execute_opcode(opcode)

        if self.delay_timer.readTimer() > 0:
            self.delay_timer.countDown()
	

	# Decrement the sound timer if it's been set
        if self.sound_timer.readTimer() > 0:
            self.sound_timer.countDown()
    def mainLoop(self):
        clock = pygame.time.Clock()

        while True:
            clock.tick(300)
            self.key_press()
            self.sound_timer.beep()
            self.cycle()
            self.display()

    def display(self):
        for i in range(0, len(self.grid)):
            for j in range(0, len(self.grid[0])):
                cellColor = self.zero_color

                if self.grid[i][j] == 1:
                    cellColor = self.one_color
                
                pygame.draw.rect(self.screen, cellColor, [j * self.screen_multiplier, i * self.screen_multiplier, self.screen_multiplier, self.screen_multiplier], 0)
        
        pygame.display.flip()



chip8 = Chip8()
chip8.readProg(sys.argv[1])
chip8.mainLoop()

