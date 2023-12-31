import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1600  # ゲームウィンドウの幅
HEIGHT = 900  # ゲームウィンドウの高さ
MAIN_DIR = os.path.split(os.path.abspath(__file__))[0]

def check_bound(obj: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内か画面外かを判定し，真理値タプルを返す
    引数 obj：オブジェクト（爆弾，こうかとん，ビーム）SurfaceのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj.left < 0 or WIDTH < obj.right:  # 横方向のはみ出し判定
        yoko = False
    if obj.top < 0 or HEIGHT < obj.bottom:  # 縦方向のはみ出し判定
        tate = False
    return yoko, tate

def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"{MAIN_DIR}/fig/{num}.png"), 0, 2.0)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 1.0),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 1.0),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 1.0),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 1.0),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 1.0),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 1.0),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "normal"
        self.hyper_life = -1

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"{MAIN_DIR}/fig/{num}.png"), 0, 2.0)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        if self.speed == 10:
            sum_mv = [0, 0]
            for k, mv in __class__.delta.items():
                if key_lst[k]:
                    self.rect.move_ip(+self.speed*mv[0], +self.speed*mv[1])
                    sum_mv[0] += mv[0]
                    sum_mv[1] += mv[1]
            if check_bound(self.rect) != (True, True):
                for k, mv in __class__.delta.items():
                    if key_lst[k]:
                        self.rect.move_ip(-self.speed*mv[0], -self.speed*mv[1])
            if not (sum_mv[0] == 0 and sum_mv[1] == 0):
                self.dire = tuple(sum_mv)
                self.image = self.imgs[self.dire]
            if self.state == "hyper":
                self.image = pg.transform.laplacian(self.image)
                self.hyper_life -= 1
            if self.hyper_life < 0:
                self.state = "normal"
        screen.blit(self.image, self.rect)


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy:"Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        self.image = pg.Surface((2*rad, 2*rad))
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        counter = random.randint(0,1)
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        if bird.speed == 10:#こうかとんが被弾していないとき
            if counter == 1:  # こうかとんに爆弾が向かっていく
                self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
                self.rect.centerx = emy.rect.centerx
                self.rect.centery = emy.rect.centery+emy.rect.height/2
                self.speed = 15
                self.state = "active"
            else:  # 爆弾が下に向かってく
                self.vx, self.vy = 0,+1  # 爆弾は真下に落ちるようにする
                self.rect.centerx = emy.rect.centerx
                self.rect.centery = emy.rect.centery+emy.rect.height/2
                self.speed = 10
                self.state = "active"
        else: # こうかとんが爆弾を被弾したとき
            self.vx, self.vy = 0,+3  # 爆弾は真下に落ちるようにする
            self.rect.centerx = emy.rect.centerx
            self.rect.centery = emy.rect.centery+emy.rect.height/2
            self.speed = 10
            self.state = "active"

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(+self.speed*self.vx, +self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"{MAIN_DIR}/fig/beam.png"), angle, 2.0)            
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(+self.speed*self.vx, +self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy|Boss", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        引数3 Boss：爆発するBoss
        """
        super().__init__()
        img = pg.image.load(f"{MAIN_DIR}/fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life
        
    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"{MAIN_DIR}/fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = random.choice(__class__.imgs)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vy = +6
        self.bound = random.randint(50, HEIGHT/2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 200)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.centery += self.vy


class Underline(pg.sprite.Sprite):
    """"
    HPゲージに関するクラス
    """
    
    def __init__(self):
        super().__init__()
        self.image = pg.image.load(f"{MAIN_DIR}/fig/緑グラデ.png") #ゲージ画像のロード
        self.hp = 800 #下画面のHP
        self.image = pg.transform.scale(self.image,(800,30)) #画像の大きさ変更
        self.rect = self.image.get_rect()
        self.rect.center = WIDTH-400,HEIGHT-50
        #self.image = pg.Surface((WIDTH,1))
        #self.underline = pg.draw.rect(self.img_gauge,(0,0,0),(0,HEIGHT-1,WIDTH,1))
        #self.rect = self.image.get_rect()

    def update(self, screen: pg.Surface):
        #self.img_gauge = self.font.render(f"HP{self.p_gauge}", 0, self.img_gauge)
        #self.image = pg.transform.scale(self.image,(800,30))
        screen.blit(self.image, self.rect)


class Underline2(pg.sprite.Sprite):
    """
    当たり判定の線に関するクラス
    """
    def __init__(self):
        super().__init__()
        self.image = pg.Surface((WIDTH,10))
        pg.draw.rect(self.image,(0,0,0),(0,HEIGHT-10,WIDTH,-100))
        self.rect = self.image.get_rect()
        self.rect.center = WIDTH/2,HEIGHT-5

    def update(self, screen: pg.Surface):
        screen.blit(self.image, self.rect)


class Boss(pg.sprite.Sprite):
    """
    ボスに関するクラス
    """
    imgs = [pg.image.load(f"{MAIN_DIR}/fig/boss.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.original_image = random.choice(__class__.imgs)
        self.image = self.original_image  # 初期画像
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vy = +6
        self.bound = random.randint(50, HEIGHT/3)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 50)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        
        self.rect.centery += self.vy
 

class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)
        

class EMP:
    def __init__(self, enemys:pg.sprite.Group, bombs:pg.sprite.Group, screan:pg.surface):
        for enemy in enemys:
            enemy.interval = math.inf
            enemy.image = pg.transform.laplacian(enemy.image)
            enemy.image.set_colorkey((0,0,0))
        for bomb in bombs:
            bomb.speed = bomb.speed/2
            bomb.state = "inactive"
        
        self.image = pg.Surface((WIDTH,HEIGHT))
        pg.draw.rect(self.image, (255,255,0),(0, 0, WIDTH, HEIGHT))
        self.image.set_alpha(128)
        screan.blit(self.image, [0,0])
        pg.display.update()
        time.sleep(0.05)
        pass


class Gravity(pg.sprite.Sprite):
    """
        超重力砲（超協力重力場）に関するclass
    """
    def __init__(self, life: int = 400):
        super().__init__()

        self.life = -life
        self.image = pg.Surface((1600, 900))
        pg.draw.rect(self.image, (0, 0, 0), (0, 0, 1600, 900))
        self.image.set_alpha(128)
        self.rect = self.image.get_rect()

    def update(self) -> None:
        if self.life >= 0:
            self.kill()
        self.life += 1
        return


class Shield(pg.sprite.Sprite):
    """
    こうかとんの前に壁が作られるクラス
    """
    def __init__(self,bird:Bird,life:int):
        super().__init__()
        self.width = 20
        self.height = bird.rect.height * 2
        self.image = pg.Surface((self.width, self.height),pg.SRCALPHA)
        pg.draw.rect(self.image, (0, 0, 255), (0, 0, self.width, self.height))
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotate(self.image, angle)
        self.rect = self.image.get_rect()
        #offset = bird.rect.width // 2
        self.rect.centerx = bird.rect.centerx + self.vx * bird.rect.width       
        self.rect.centery = bird.rect.centery + self.vy * bird.rect.height
        self.life = life


    def update(self):
        self.life -= 1
        if self.life<0:
            self.kill()
        
        
class Alien(pg.sprite.Sprite):
    imgal = [pg.image.load(f"{MAIN_DIR}/fig/utyujin{i}.png") for i in range(1, 3)]
    
    def __init__(self, bird: Bird):
        super().__init__()
        self.image = random.choice(__class__.imgal)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = calc_orientation(self.rect, bird.rect)  
        
        self.speed = 8
        
    def update(self):
        """
        宇宙人を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(+self.speed*self.vx, +self.speed*self.vy)
        
        
class Conbeam(pg.sprite.Sprite):
    """
    連続的なビームに関するクラス
    """
    def __init__(self,bird: Bird, life: int=100):
        super().__init__()
        """
        ビームを生成する
        連続的なビームを放つこうかとん
        """
        self.vx, self.vy = bird.dire
        self.life = -life
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"{MAIN_DIR}/fig/beam_blue.png"), angle, 2.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centerx = bird.rect.centerx + self.vx * bird.rect.width * 8.5 #ビームの画像がこうかとんの画像の約8.5倍
        self.rect.centery = bird.rect.centery + self.vy * bird.rect.height * 8.5
        self.speed = 1

    def update(self) -> None:
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(+self.speed*self.vx, +self.speed*self.vy) #ビームを動かす
        if self.life >= 0:
            self.kill()
        self.life += 1
        return


def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    #bg_img = pg.image.load(f"{MAIN_DIR}/fig/pg_bg.jpg")
    bg_img = pg.transform.rotozoom(pg.image.load(f"{MAIN_DIR}/fig/pg_bg.jpg"), 0, 3.5)
    score = Score()
    stoptime = 0  # こうかとんが動けなくなる時間を格納
    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    gravitys = pg.sprite.Group()
    shis = pg.sprite.Group()
    conbeams = pg.sprite.Group()
    boss = pg.sprite.Group()
    aliens = pg.sprite.Group()
    underline = Underline()
    underline2 = Underline2()
    tmr = 0
    clock = pg.time.Clock()

    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                beams.add(Beam(bird))
                
            if event.type == pg.KEYDOWN and event.key == pg.K_e:
                if score.value > 20:
                    EMP(emys, bombs, screen)
                    score.value -= 20

            # スコアが100を超えたらBossを生成
            if score.value >= 100 and len(boss) == 0:
                boss.add(Boss())
            
            for bos in boss:
                if bos.state == "stop" and tmr%bos.interval == 0:
                    # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                    bombs.add(Bomb(bos, bird))        

            if event.type == pg.KEYDOWN and event.key == pg.K_RSHIFT and score.value >= 100:
                bird.state = "hyper"
                bird.hyper_life = 500
                score.value -= 100
            
            if event.type == pg.KEYDOWN and event.key == pg.K_RETURN and score.value >= 200:
                gravitys.add(Gravity())
                score.value -= 200

            #100スコアを消費して連続的なビームを打つ
            if event.type == pg.KEYDOWN and event.key == pg.K_b and score.value >= 100:
                conbeams.add(Conbeam(bird))
                score.value -= 100

        if  len(gravitys) == 0:
            screen.blit(bg_img, [0, 0])
            if event.type == pg.KEYDOWN and event.key == pg.K_CAPSLOCK:
                if score.value>50 and len(shis)==0:
                    shis.add(Shield(bird,400))
                    score.value-=50
        
        screen.blit(bg_img, [0, 0])
        if event.type == pg.KEYDOWN and event.key == pg.K_LSHIFT:
            bird.speed = 20
             
        if event.type == pg.KEYUP and event.key == pg.K_LSHIFT:
            bird.speed = 10
                
        if tmr%200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())
            
        if tmr%300 == 0: # 300フレームに1回、宇宙人を出現させる
            aliens.add(Alien(bird))
            
        for emy in emys:
            if emy.state == "stop" and tmr%emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))
        
        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト
            
        for bos in pg.sprite.groupcollide(boss, beams, True, True).keys():
            exps.add(Explosion(bos, 200))  # 爆発エフェクト
            score.value += 100  # 100点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ
            
        for alien in pg.sprite.groupcollide(aliens, beams, True, True).keys():
            exps.add(Explosion(alien, 100))  # 爆発エフェクト
            score.value += 5  # 5点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト
        
        for bomb in pg.sprite.groupcollide(shis,bombs,True,True).keys():
            exps.add(Explosion(bomb,50))

        for bomb in pg.sprite.spritecollide(underline2,bombs,True): #爆弾が下の画面に衝突した時
            underline.hp -= 100 #HPを10減らす
            pg.draw.rect(underline.image,(255,255,255),[underline.hp,0, 100, 100]) #ダメージを受けたら短形を塗りつぶす
            if underline.hp <= 0: #HPが0以下になったら
                 bird.change_img(8, screen) # こうかとん悲しみエフェクト
                 score.update(screen)
                 pg.display.update()
                 time.sleep(2)
                 return

        for bomb in pg.sprite.spritecollide(bird, bombs, True):
            if bird.state == "normal":
                bird.change_img(8, screen) # こうかとん悲しみエフェクト
                bird.speed = 0  # こうかとんのスピードを0にして動けないようにする
                stoptime = 0  # 新しく爆弾に当たったら止まる時間を0にする
                score.update(screen)
                pg.display.update()
            if bird.state == "hyper":
                exps.add(Explosion(bomb, 50))  # 爆発エフェクト
                score.value += 1
        
        for bomb in pg.sprite.spritecollide(bird, bombs, True):
            if bomb.state == "inactive":
                continue
            bird.change_img(8, screen) # こうかとん悲しみエフェクト
            score.update(screen)
            pg.display.update()
        
        if bird.speed == 0:  #爆弾に当たってこうかとんが動かなくなったら
            stoptime+=1  # 動けない時間のカウントをはじめる
            if stoptime >= 80:  # 動けない時間が80を超えたら
                bird.speed = 10  # こうかとんをうごけるようにする
                stoptime = 0  # 動けない時間を初期化する

        for alien in pg.sprite.spritecollide(bird, aliens, True):
            if bird.state == "normal":
                bird.change_img(8, screen) # こうかとん悲しみエフェクト
                score.update(screen)
                pg.display.update()
                time.sleep(2)
                return
            if bird.state == "hyper":
                exps.add(Explosion(bomb, 50))  # 爆発エフェクト
                score.value += 5
        
        for emy in pg.sprite.groupcollide(emys, gravitys, True, False).keys():
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト
        for bomb in pg.sprite.groupcollide(bombs, gravitys, True, False).keys():
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        for emy in pg.sprite.groupcollide(emys, conbeams, True, False).keys():
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト
        for bomb in pg.sprite.groupcollide(bombs, conbeams, True, False).keys():
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ
        
        
        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        aliens.update()
        aliens.draw(screen)
        exps.update()
        exps.draw(screen)
        gravitys.update()
        gravitys.draw(screen)
        conbeams.update()
        conbeams.draw(screen)
        boss.update()  # Bossを更新
        boss.draw(screen)  # Bossを描画
        shis.update()
        shis.draw(screen)
        score.update(screen)
        underline.update(screen)
        underline2.update(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
