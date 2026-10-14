import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Select
import os
import io
import time
import asyncio
import random
import math
import contextlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from games.meono_logic import Deck, Card

# --- ASYNC LOCK ---
_action_locks = {}

@contextlib.asynccontextmanager
async def is_action_locked(user_id):
    if user_id not in _action_locks:
        _action_locks[user_id] = asyncio.Lock()
    
    if _action_locks[user_id].locked():
        yield True
    else:
        async with _action_locks[user_id]:
            yield False

# --- CONSTANTS & EMOJIS ---
EMOJIS = {
    'exploding': '💣',
    'defuse': '🛡️',
    'nope': '🚫',
    'attack': '⚔️',
    'skip': '⏭️',
    'favor': '🎁',
    'shuffle': '🔀',
    'future': '👁️',
    'cat': '🐱'
}

COLORS = {
    'exploding': (200, 40, 40),
    'defuse': (46, 204, 113),
    'nope': (231, 76, 60),
    'attack': (230, 126, 34),
    'skip': (52, 152, 219),
    'favor': (155, 89, 182),
    'shuffle': (149, 165, 166),
    'future': (241, 196, 15),
    'cat': (243, 156, 18)
}

# --- RENDERER (HÌNH QUẠT ĐẸP MẮT) ---
class MeoNoRenderer:
    BASE_DIR = "assets/image_meono"
    
    @staticmethod
    def ensure_dir_exists():
        if not os.path.exists(MeoNoRenderer.BASE_DIR):
            os.makedirs(MeoNoRenderer.BASE_DIR)

    @staticmethod
    def draw_placeholder(card, w=200, h=300):
        # Nền gradient nhẹ giả lập shadow
        img = Image.new("RGBA", (w, h), (30, 30, 35, 255))
        draw = ImageDraw.Draw(img)
        
        main_color = COLORS.get(card.type, (200, 200, 200))
        # Viền Premium Glass
        draw.rounded_rectangle((5, 5, w-5, h-5), radius=15, outline=main_color, width=12)
        draw.rounded_rectangle((12, 12, w-12, h-12), radius=8, outline=(80, 80, 80), width=2)
        
        try: font_large = ImageFont.truetype("assets/font.ttf", 36)
        except: font_large = ImageFont.load_default()
        try: font_small = ImageFont.truetype("assets/font.ttf", 22)
        except: font_small = ImageFont.load_default()
        
        emoji = EMOJIS.get(card.type, '❓')
        
        # Vẽ emoji to ở góc
        draw.text((w/2 - 20, 20), emoji, font=font_large, fill=main_color)
        
        # Xử lý cắt Text tự động (Word Wrap)
        text = card.name.upper()
        words = text.split()
        if len(words) > 2:
            lines = [" ".join(words[:2]), " ".join(words[2:])]
        else:
            lines = [text]
            
        y_text = h/2 - 30
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font_large)
            text_w = bbox[2] - bbox[0]
            draw.text(((w - text_w)/2, y_text), line, font=font_large, fill=(255, 255, 255))
            y_text += 40
            
        # Dải băng System dưới cùng ghi loại thẻ
        draw.rounded_rectangle((12, h-45, w-12, h-12), radius=8, fill=main_color)
        t_bbox = draw.textbbox((0,0), card.type.upper(), font=font_small)
        draw.text(((w - (t_bbox[2]-t_bbox[0]))/2, h-40), card.type.upper(), font=font_small, fill=(20, 20, 20))
        
        return img

    @staticmethod
    def create_hand_image(cards, player_name=""):
        if not cards: return None
        MeoNoRenderer.ensure_dir_exists()
        images = []
        is_board = len(cards) == 1 and player_name.startswith("Vừa ném")
        card_w, card_h = (280, 420) if is_board else (200, 300)
        
        for card in cards:
            path = os.path.join(MeoNoRenderer.BASE_DIR, card.image_name)
            try:
                img = Image.open(path).convert("RGBA")
                img = img.resize((card_w, card_h), Image.Resampling.LANCZOS)
            except FileNotFoundError:
                img = MeoNoRenderer.draw_placeholder(card, card_w, card_h)
            images.append(img)
            
        qty = len(images)
        if qty == 0: return None
        
        # Góc bo tạo hình cánh quạt
        max_angle = min(25, qty * 2.8) 
        x_spacing = 75 if qty < 10 else 50
        y_curve_factor = 1.0
        
        # Căn chỉnh Canvas
        fan_width = (qty - 1) * x_spacing + card_w
        canvas_width = max(850, fan_width + 150)
        canvas_height = card_h + int(max_angle * 5) + 140
        
        # Canvas nền trong suốt (RGBA)
        result_image = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(result_image)
        
        # Text Header tay bài
        try: font = ImageFont.truetype("assets/font.ttf", 36)
        except: font = ImageFont.load_default()
        
        name_text = f"Tay bài của: {player_name}" if not is_board else player_name
        bbox = draw.textbbox((0,0), name_text, font=font)
        # Background cho Text
        draw.rounded_rectangle(((canvas_width - (bbox[2]-bbox[0]))/2 - 20, 10, (canvas_width + (bbox[2]-bbox[0]))/2 + 20, 60), radius=15, fill=(0,0,0,180))
        draw.text(((canvas_width - (bbox[2]-bbox[0]))/2, 15), name_text, font=font, fill=(255, 215, 0))
        
        start_x = (canvas_width - fan_width) // 2
        base_y = 90
        center_idx = (qty - 1) / 2 
        
        for i, img_card in enumerate(images):
            if qty == 1: angle = 0
            else:
                ratio = (i - center_idx) / center_idx
                angle = ratio * max_angle
                
            rotated_img = img_card.rotate(-angle, expand=True, resample=Image.BICUBIC)
            x = start_x + (i * x_spacing) + (card_w // 2) - (rotated_img.width // 2)
            y_drop = abs(angle) * y_curve_factor * 2.5
            y = base_y + y_drop + (card_h // 2) - (rotated_img.height // 2)
            
            # Gắn bóng mờ 3D phía sau bài
            shadow = Image.new('RGBA', rotated_img.size, (0,0,0,0))
            shadow.paste((0,0,0,180), (0,0), rotated_img)
            result_image.paste(shadow, (int(x)+3, int(y)+6), shadow)
            
            # Dán lá bài thật
            result_image.paste(rotated_img, (int(x), int(y)), rotated_img)
            
        img_byte_arr = io.BytesIO()
        result_image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        return discord.File(fp=img_byte_arr, filename=f"hand_{int(time.time()*100)}.png")

# --- UI COMPONENTS TƯƠNG TÁC DISCORD ---
class CardButton(Button):
    def __init__(self, card, view_parent, unique_id):
        emoji_str = EMOJIS.get(card.type, '🃏')
        self.card = card
        self.unique_id = unique_id
        self.view_parent = view_parent
        
        is_selected = self.unique_id in self.view_parent.selected_ids
        style = discord.ButtonStyle.success if is_selected else discord.ButtonStyle.secondary
        
        super().__init__(style=style, label=card.name, emoji=emoji_str, row=None)

    async def callback(self, interaction: discord.Interaction):
        if self.unique_id in self.view_parent.selected_ids:
            self.view_parent.selected_ids.remove(self.unique_id)
        else:
            self.view_parent.selected_ids.append(self.unique_id)
        
        self.view_parent.create_hand_ui()
        await interaction.response.edit_message(view=self.view_parent)


class HandInteractiveView(View):
    def __init__(self, main_game, user_id):
        super().__init__(timeout=None)
        self.main_game = main_game
        self.user_id = user_id
        self.selected_ids = []
        self.create_hand_ui()
        
    async def ghost_check(self, interaction):
        if getattr(self.main_game, "is_game_over", False):
            await interaction.response.send_message("❌ LỖI KHÔNG GIAN: Phiên bản tay bài này thuộc về ván CŨ đã kết thúc. Hãy tương tác với bàn cờ mới nhất!", ephemeral=True)
            return True
        return False

    def create_hand_ui(self):
        self.clear_items()
        hand = self.main_game.hands.get(self.user_id, [])
        
        for i, card in enumerate(hand):
            if i >= 20: 
                break
            btn = CardButton(card, self, f"card_{i}")
            self.add_item(btn)
            
        count = len(self.selected_ids)
        if count > 0:
            btn_play = Button(label=f"🚀 ĐÁNH ({count})", style=discord.ButtonStyle.primary, row=4)
            btn_play.callback = self.play_callback
            self.add_item(btn_play)
            
            btn_clear = Button(label="Bỏ chọn", style=discord.ButtonStyle.danger, row=4)
            btn_clear.callback = self.clear_callback
            self.add_item(btn_clear)
            
        btn_refresh = Button(label="Tải lại", style=discord.ButtonStyle.secondary, row=4)
        btn_refresh.callback = self.refresh_callback
        self.add_item(btn_refresh)
        
        btn_draw = Button(label="Bốc Bài Ngay", style=discord.ButtonStyle.danger, row=4, emoji="👇")
        btn_draw.callback = self.draw_callback
        self.add_item(btn_draw)

    async def clear_callback(self, interaction: discord.Interaction):
        if await self.ghost_check(interaction): return
        self.selected_ids = []
        self.create_hand_ui()
        await interaction.response.edit_message(view=self)

    async def play_callback(self, interaction: discord.Interaction):
        if await self.ghost_check(interaction): return
        if getattr(self.main_game, "is_action_locked", False):
            return await interaction.response.send_message("⏳ Đang có hành động khác trên bàn cờ. Vui lòng đợi xử lý xong!", ephemeral=True)
            
        if self.main_game.current_player.id != interaction.user.id:
            return await interaction.response.send_message("❌ Chưa tới lượt của bạn!", ephemeral=True)
            
        hand = self.main_game.hands[self.user_id]
        cards_to_play = []
        for uid in self.selected_ids:
            idx = int(uid.split("_")[1])
            if idx < len(hand):
                cards_to_play.append(hand[idx])
                
        if not cards_to_play:
             return await interaction.response.send_message("⚠️ Có lỗi đồng bộ dữ liệu tay bài!", ephemeral=True)
             
        count = len(cards_to_play)
        is_combo = False
        if count == 2:
            if cards_to_play[0].name != cards_to_play[1].name:
                return await interaction.response.send_message("Cặp bài phải giống nhau hoàn toàn mới tính là Combo Bắt Cặp!", ephemeral=True)
            is_combo = True
        elif count == 3:
            if not all(c.name == cards_to_play[0].name for c in cards_to_play):
                 return await interaction.response.send_message("Bộ ba phải giống nhau hoàn toàn!", ephemeral=True)
            is_combo = True
        elif count == 5:
            names = set(c.name for c in cards_to_play)
            if len(names) != 5:
                return await interaction.response.send_message("Bộ ngũ hầm xí phải là 5 lá khác nhau hoàn toàn!", ephemeral=True)
            is_combo = True
        elif count == 1:
            if cards_to_play[0].type not in ['action', 'nope', 'attack', 'skip', 'favor', 'shuffle', 'future']:
                return await interaction.response.send_message("⚠️ Lá này là bài thường, bạn cần rủ thêm lá khác để ghép Combo!", ephemeral=True)
        else:
             return await interaction.response.send_message("⚠️ Bộ quy tắc chỉ hỗ trợ combo 2, 3 và 5 lá!", ephemeral=True)
             
        await interaction.response.defer()
        
        self.main_game.is_action_locked = True
        try:
            requires_target = False
            if count in [2, 3] or (count == 1 and cards_to_play[0].type == "favor"):
                requires_target = True

            victim = None
            if requires_target:
                players_to_rob = [p for p in self.main_game.players if p.id != self.user_id and self.main_game.lives[p.id] and len(self.main_game.hands[p.id])>0]
                if not players_to_rob:
                    return await interaction.followup.send("❌ Không có ai còn sống hoặc có bài để bạn chĩa mũi nhọn!", ephemeral=True)
                    
                target_view = TargetSelectView(players_to_rob)
                await interaction.edit_original_response(content="🎯 **Vui lòng chọn nạn nhân** ở menu bên dưới để chốt mục tiêu:", view=target_view, attachments=[])
                await target_view.wait()
                
                if not target_view.selected_target_id:
                    return 
                    
                victim = next(p for p in players_to_rob if p.id == target_view.selected_target_id)
            
            for c in cards_to_play:
                hand.remove(c)
                self.main_game.discard_pile.append(c)
                
            player_hand = self.main_game.hands[self.user_id]
            file = MeoNoRenderer.create_hand_image(player_hand, interaction.user.display_name)
            await interaction.edit_original_response(content=f"⏳ Vừa đánh **{cards_to_play[0].name if count==1 else 'Combo'}**... ", attachments=[file] if file else [], view=None)
            
            action_name = cards_to_play[0].name if count == 1 else f"Combo {count} lá"
            if victim:
                action_name += f" nhắm vào {victim.display_name}"
                
            emoji = EMOJIS.get(cards_to_play[0].type, "💥") if count == 1 else "💥"
            
            nope_view = NopeWaitView(self.main_game)
            embed = discord.Embed(title="🚫 LĨNH VỰC NOPE", description=f"**{interaction.user.display_name}** vừa dộng **{action_name}** xuống bàn!\nAi có thẻ NOPE tung ra ngay!", color=0xE74C3C)
            nope_msg = await self.main_game.message.channel.send(embed=embed, view=nope_view)
            
            last_noped = 0
            while True:
                await asyncio.sleep(6.0)
                if nope_view.noped_count == last_noped:
                    break
                last_noped = nope_view.noped_count
                
            nope_view.stop()
            try: await nope_msg.delete()
            except: pass
            
            if nope_view.noped_count % 2 != 0:
                self.main_game.add_log(f"❌ {emoji} Khá khen! Đòn **{action_name}** đã bị HUỶ vì dính NOPE!")
                self.main_game.last_played_card = cards_to_play[-1]
                self.main_game.last_action_player = interaction.user
                await self.main_game.update_board()
                
                player_hand = self.main_game.hands[self.user_id]
                file = MeoNoRenderer.create_hand_image(player_hand, interaction.user.display_name)
                new_view = HandInteractiveView(self.main_game, self.user_id)
                try: await interaction.edit_original_response(content=f"❌ Bị gián đoạn! Phép **{action_name}** đã bị dính NOPE nên mất tác dụng!", attachments=[file] if file else [], view=new_view)
                except: pass
                return
                
            self.main_game.add_log(f"{emoji} Hành động **{action_name}** được thực thi thành công!")
            
            if count == 1:
                c_type = cards_to_play[0].type
                if c_type == "skip":
                    self.main_game.next_turn()
                elif c_type == "attack":
                    curr_pending = self.main_game.pending_turns[self.user_id]
                    extra = curr_pending + 1 if curr_pending > 0 else 2
                    self.main_game.pending_turns[self.user_id] = 0
                    self.main_game.next_turn()
                    tgt = self.main_game.current_player.id
                    if self.main_game.pending_turns[tgt] == 1: self.main_game.pending_turns[tgt] = extra
                    else: self.main_game.pending_turns[tgt] += extra
                elif c_type == "shuffle":
                    random.shuffle(self.main_game.deck.cards)
                elif c_type == "future":
                    top3 = [c.name for c in self.main_game.deck.cards[-3:]]
                    top3.reverse()
                    await interaction.followup.send(f"🔮 Tiên tri: 3 lá trên cùng nọc là:\n1. **{top3[0]}**\n2. **{top3[1] if len(top3)>1 else 'Hết'}**\n3. **{top3[2] if len(top3)>2 else 'Hết'}**", ephemeral=True)
                elif c_type == "favor":
                    if victim:
                        v_hand = self.main_game.hands[victim.id]
                        # Gửi menu chọn lá cho nạn nhân
                        favor_view = FavorGiveView(v_hand, victim)
                        favor_embed = discord.Embed(
                            title="🎁 BẠN BỊ ĐÒI QUÀ (FAVOR)!",
                            description=f"**{interaction.user.display_name}** đang đòi bạn nộp 1 lá bài!\nHãy chọn lá bạn muốn cho đi (30 giây).",
                            color=0x9B59B6
                        )
                        favor_msg = await self.main_game.message.channel.send(
                            content=victim.mention,
                            embed=favor_embed,
                            view=favor_view
                        )
                        await favor_view.wait()
                        
                        chosen_idx = favor_view.chosen_index
                        if chosen_idx is not None and chosen_idx < len(v_hand):
                            stolen = v_hand[chosen_idx]
                        else:
                            stolen = random.choice(v_hand)
                        
                        v_hand.remove(stolen)
                        hand.append(stolen)
                        self.main_game.add_log(f"🎁 Favor! {victim.display_name} đã nộp 1 lá cho {interaction.user.display_name}.")
                        await self.main_game.sync_hand_ui(victim.id)
                        try: await favor_msg.delete()
                        except: pass
            elif count == 2:
                if victim:
                    v_hand = self.main_game.hands[victim.id]
                    stolen = random.choice(v_hand)
                    v_hand.remove(stolen)
                    hand.append(stolen)
                    self.main_game.add_log(f"Giật tuột 1 lá ngẫu nhiên từ {victim.display_name}.")
                    await self.main_game.sync_hand_ui(victim.id)
            elif count == 3:
                if victim:
                    v_hand = self.main_game.hands[victim.id]
                    stolen = v_hand[0]
                    v_hand.remove(stolen)
                    hand.append(stolen)
                    self.main_game.add_log(f"🎯 Bộ Ba! Trực tiếp tước đoạt lá bài tủ của {victim.display_name}.")
                    await self.main_game.sync_hand_ui(victim.id)
            elif count == 5:
                if self.main_game.discard_pile:
                    stolen = random.choice(self.main_game.discard_pile)
                    self.main_game.discard_pile.remove(stolen)
                    hand.append(stolen)
                    self.main_game.add_log(f" 🧟 Bộ Năm! Trùng tu lại 1 lá bài từ nghĩa địa.")
            
            self.main_game.last_played_card = cards_to_play[-1]
            self.main_game.last_action_player = interaction.user
            await self.main_game.update_board()
            
            try: 
                player_hand = self.main_game.hands[self.user_id]
                file = MeoNoRenderer.create_hand_image(player_hand, interaction.user.display_name)
                new_view = HandInteractiveView(self.main_game, self.user_id)
                await interaction.edit_original_response(content=f"✅ Giông bão qua đi, Đã thi triển **{action_name}** trót lọt!", attachments=[file] if file else [], view=new_view)
                self.main_game.hand_interactions[self.user_id] = interaction
            except: pass
        finally:
            self.main_game.is_action_locked = False
        
    async def draw_callback(self, interaction: discord.Interaction):
        if await self.ghost_check(interaction): return
        await self.main_game.perform_draw(interaction, is_from_hand_view=True)

    async def refresh_callback(self, interaction: discord.Interaction):
        if await self.ghost_check(interaction): return
        player_hand = self.main_game.hands[self.user_id]
        file = MeoNoRenderer.create_hand_image(player_hand, interaction.user.display_name)
        new_view = HandInteractiveView(self.main_game, self.user_id)
        await interaction.response.edit_message(attachments=[file], view=new_view)
        self.main_game.hand_interactions[self.user_id] = interaction

class TargetSelectView(discord.ui.View):
    def __init__(self, targets):
        super().__init__(timeout=60.0)
        self.selected_target_id = None
        
        options = [discord.SelectOption(label=p.display_name, value=str(p.id)) for p in targets]
        self.select = discord.ui.Select(placeholder="Chọn nạn nhân...", options=options)
        self.select.callback = self.select_callback
        self.add_item(self.select)
        
    async def select_callback(self, interaction: discord.Interaction):
        self.selected_target_id = int(self.select.values[0])
        await interaction.response.defer()
        self.stop()


class FavorGiveView(discord.ui.View):
    """View cho nạn nhân tự chọn lá bài để nộp khi bị Favor."""
    def __init__(self, victim_hand, victim_user):
        super().__init__(timeout=30.0)
        self.chosen_index = None
        self.victim_user = victim_user
        
        options = []
        for i, card in enumerate(victim_hand):
            emoji = EMOJIS.get(card.type, '❓')
            options.append(discord.SelectOption(
                label=f"{card.name}",
                value=str(i),
                emoji=emoji,
                description=f"Loại: {card.type}"
            ))
            if i >= 24:  # Discord giới hạn 25 options
                break
        
        self.select = discord.ui.Select(
            placeholder="🎁 Chọn 1 lá bài để nộp cho đối phương...",
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)
    
    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.victim_user.id:
            return await interaction.response.send_message("❌ Chỉ nạn nhân mới được chọn lá để nộp!", ephemeral=True)
        self.chosen_index = int(self.select.values[0])
        await interaction.response.send_message("✅ Đã chọn! Lá bài đang được chuyển giao...", ephemeral=True)
        self.stop()
        
class NopeWaitView(View):
    def __init__(self, main_game):
        super().__init__(timeout=None)
        self.main_game = main_game
        self.noped_count = 0
        
    @discord.ui.button(label="SAY NOPE!", style=discord.ButtonStyle.danger, emoji="🚫")
    async def btn_nope(self, interaction: discord.Interaction, button: Button):
        hand = self.main_game.hands.get(interaction.user.id, [])
        nope_card = next((c for c in hand if c.type == 'nope'), None)
        if not nope_card:
            return await interaction.response.send_message("❌ Múa mồm vô dụng! Bạn không có lá Nope trong tay!", ephemeral=True)
            
        hand.remove(nope_card)
        self.main_game.discard_pile.append(nope_card)
        self.noped_count += 1
        
        state = "BỊ NOPE!" if self.noped_count % 2 == 1 else "NOPE LẠI NOPE (CHẤP NHẬN)!"
        self.main_game.add_log(f"🚫 **{interaction.user.display_name}** quăng thẻ Nope chặn đứng! Tình trạng: **{state}**")
        
        await self.main_game.update_board()
        await interaction.response.send_message("✅ Đã chưởng lá NOPE thành công!", ephemeral=True)
        await self.main_game.sync_hand_ui(interaction.user.id)

class MeoNoGameView(View):
    def __init__(self, owner):
        super().__init__(timeout=None)
        self.owner = owner
        self.players = [owner]
        self.started = False
        self.is_game_over = False
        self.message = None
        
        self.deck = None
        self.hands = {}  
        self.turn_queue = [] 
        self.current_player = None
        self.lives = {} 
        self.logs = ["📢 Game được lập! Chờ người tham gia..."]
        self.last_played_card = None
        self.last_action_player = None
        self.discard_pile = []
        self.pending_turns = {}
        self.hand_interactions = {}
        
        self.setup_lobby()

    def add_log(self, text):
        self.logs.insert(0, text)
        if len(self.logs) > 6:
            self.logs.pop()

    async def cleanup(self):
        self.is_game_over = True
        self.started = False
        if self.message:
            try: await self.message.delete()
            except: pass

    async def sync_hand_ui(self, user_id):
        if user_id in self.hand_interactions:
            inter = self.hand_interactions[user_id]
            try:
                player_hand = self.hands.get(user_id, [])
                user = next((p for p in self.players if p.id == user_id), None)
                if not user: return
                file = MeoNoRenderer.create_hand_image(player_hand, user.display_name)
                new_view = HandInteractiveView(self, user_id)
                await inter.edit_original_response(content="⚠️ BÀI CỦA BẠN VỪA BỊ BIẾN ĐỘNG!", attachments=[file] if file else [], view=new_view)
            except Exception:
                pass

    def setup_lobby(self):
        self.clear_items()
        btn_join = Button(label="Tham Gia", style=discord.ButtonStyle.blurple, emoji="🙋")
        btn_join.callback = self.join_callback
        self.add_item(btn_join)
        
        btn_start = Button(label="Bắt Đầu Mèo Nổ", style=discord.ButtonStyle.green, emoji="🚀")
        btn_start.callback = self.start_callback
        self.add_item(btn_start)

        btn_guide = Button(label="Hướng Dẫn", style=discord.ButtonStyle.gray, emoji="📖")
        btn_guide.callback = self.guide_callback
        self.add_item(btn_guide)

    async def guide_callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 HƯỚNG DẪN CHI TIẾT: MÈO NỔ (EXPLODING KITTENS)",
            description=(
                "**1. Luật chơi sinh tồn:**\n"
                "• Rút bài theo lượt từ nọc bài chung. Ai rút trúng **Mèo Nổ (Exploding Kitten)** mà không có lá **Gỡ bom (Defuse)** để giải nguy thì sẽ bị loại (Banh Xác) ngay lập tức!\n"
                "• Người chơi cuối cùng còn sống sót trên bàn cờ là người chiến thắng.\n\n"
                "**2. Chức năng chi tiết các lá bài:**\n"
                "• 🛡️ **Gỡ Bom (Defuse):** Cứu mạng khi bốc trúng Mèo Nổ. Sau khi dùng, Mèo Nổ được lén đặt lại vào vị trí bất kỳ trong nọc bài để gài bẫy người khác.\n"
                "• ⚔️ **Tấn Công (Attack):** Kết thúc lượt mà không cần bốc bài, bắt người tiếp theo phải đi thêm 1 lượt bốc (phạt dồn lượt).\n"
                "• 🏃 **Bỏ Lượt (Skip):** Kết thúc lượt của bạn ngay lập tức mà không cần bốc bài.\n"
                "• 🔮 **Xem Trước Tương Lai (See the Future):** Nhìn lén 3 lá bài đầu tiên trên cùng của nọc bài.\n"
                "• 🔄 **Tráo Bài (Shuffle):** Tráo ngẫu nhiên lại toàn bộ nọc bài chung.\n"
                "• 🎁 **Ủng Hộ (Favor):** Bắt 1 người chơi khác tự chọn và nộp 1 lá bài của họ cho bạn.\n"
                "• 🚫 **Chặn Đứng (Nope):** Hủy bỏ tác dụng của lá bài vừa đánh (trừ Mèo Nổ & Defuse). Có thể đè Nope chồng Nope (Double Nope = Đồng ý).\n\n"
                "**3. Các Combo thẻ bài thường (Không chức năng đơn):**\n"
                "• **Combo 2 lá giống nhau:** Chọn 1 người để cướp ngẫu nhiên 1 lá bài từ tay họ.\n"
                "• **Combo 3 lá giống nhau:** Chọn 1 người và gọi tên 1 lá bài. Nếu họ có, họ bắt buộc phải nộp lá đó cho bạn.\n"
                "• **Combo 5 lá khác nhau:** Được phép chọn lấy lại 1 lá bài bất kỳ từ nghĩa địa (mộ bài đã đánh).\n\n"
                "**4. Cách thao tác với Bot:**\n"
                "• Bấm **'Quản Lý Bài'** để mở bảng điều khiển bài cá nhân gửi riêng cho bạn (ẩn danh).\n"
                "• Chọn các lá bài rồi bấm **'🚀 ĐÁNH'** để sử dụng/ghép combo. Hoặc bấm **'Bốc Bài Ngay'** để kết thúc lượt của mình bằng cách bốc bài.\n"
                "• Khi có người đánh bài, nút **'SAY NOPE!'** sẽ hiện trên bàn cờ chính để bạn nhấn tranh cướp chặn đòn nếu có thẻ Nope."
            ),
            color=0xE74C3C
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    async def join_callback(self, interaction: discord.Interaction):
        if self.started: return await interaction.response.send_message("❌ Game đã bắt đầu!", ephemeral=True)
        if interaction.user in self.players:
            return await interaction.response.send_message("⚠️ Bạn đã tham gia roi!", ephemeral=True)
        self.players.append(interaction.user)
        self.add_log(f"👋 **{interaction.user.display_name}** đã liều mạng tham gia.")
        await interaction.response.send_message(f"✅ Đã tham gia thành công. Ngồi ngoan chờ host Bắt đầu!", ephemeral=True)
        await self.update_board()

    async def start_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner.id:
            return await interaction.response.send_message("❌ Chỉ có Host phòng mới được bấm!", ephemeral=True)
        if len(self.players) < 2:
            return await interaction.response.send_message("⚠️ Mèo móng vuốt rất sắc, phải có từ 2 người trở lên để chơi!", ephemeral=True)
            
        self.started = True
        self.deck = Deck(len(self.players))
        hands = self.deck.deal()
        
        for i, player in enumerate(self.players):
            self.hands[player.id] = hands[i]
            self.lives[player.id] = True
            self.pending_turns[player.id] = 1
            
        self.turn_queue = [p for p in self.players]
        self.current_player = self.turn_queue[0]
        
        self.logs = [f"🚀  BẮT ĐẦU với {len(self.players)} tay liều mạng!"]
        
        self.clear_items()
        btn_hand = Button(label="Quản Lý Bài", style=discord.ButtonStyle.primary, emoji="🎴")
        btn_hand.callback = self.view_hand_callback
        self.add_item(btn_hand)
        
        btn_draw = Button(label="Bốc Bài", style=discord.ButtonStyle.danger, emoji="👇")
        btn_draw.callback = self.draw_card_callback
        self.add_item(btn_draw)

        btn_guide = Button(label="Hướng Dẫn", style=discord.ButtonStyle.gray, emoji="📖")
        btn_guide.callback = self.guide_callback
        self.add_item(btn_guide)
        
        await interaction.response.defer()
        await self.update_board()

    async def update_board(self, notice_embed=None):
        if not self.started:
            p_list = "\n".join([f"🔸 **{p.display_name}**" for p in self.players])
            embed = discord.Embed(title="💣 PHÒNG CHỜ MÈO NỔ 💣", description="Triệu tập chiến binh chơi bài sinh tử...", color=0xE74C3C)
            embed.add_field(name=f"👥 Người chơi tham chiến ({len(self.players)})", value=p_list)
            embed.set_footer(icon_url=self.owner.display_avatar.url, text=f"Chủ phòng: {self.owner.display_name}")
            if self.message: await self.message.edit(embed=embed, view=self)
            return

        active_players = [p for p in self.players if self.lives[p.id]]
        if len(active_players) == 1:
            winner = active_players[0]
            embed = discord.Embed(title="🏆 TRÒ CHƠI KẾT THÚC!", description=f"🎉 CHÚC MỪNG MÈO PHÙ THỦY **{winner.mention}** là kẻ sống sót cuối cùng vươn lên đỉnh cao!", color=0xF1C40F)
            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1458674262293614685/1460560226506903685/Season_3_Revolver_GIF_by_The_Simpsons.gif") 
            if self.message: await self.message.edit(embed=embed, view=None)
            return
            
        embed = discord.Embed(title="💣 BÀN CỜ ĐỊNH MỆNH: EXPLODING KITTENS 💣", color=0xE74C3C)
        embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/en/thumb/f/fa/Exploding_Kittens_box_art.jpg/220px-Exploding_Kittens_box_art.jpg")
        msg_header = f"🔥 Tới Lượt Quyết Định: {self.current_player.mention}"
        
        # UI Tình Trạng
        status = ""
        for p in self.players:
            if not self.lives[p.id]:
                status += f"💀 ~~{p.display_name}~~ *(Banh Xác)*\n"
            else:
                pointer = "👉 **" if p.id == self.current_player.id else "🔹 "
                suffix = "**" if p.id == self.current_player.id else ""
                c_count = len(self.hands[p.id])
                
                turns = self.pending_turns.get(p.id, 1)
                turn_str = f" ⚔️(`Phạt {turns} bốc`)" if turns > 1 and p.id == self.current_player.id else ""
                
                status += f"{pointer}{p.display_name}{suffix}: `{c_count} lá` 🎴{turn_str}\n"
        
        embed.add_field(name="👥 Danh Sách Tế Thần", value=status, inline=True)
        
        # Mạch đập trái tim (Deck size UX)
        deck_size = len(self.deck.cards)
        progress_blocks = min(10, max(1, math.ceil(deck_size / max(1, len(self.players)*2))))
        progress_bar = "🟥" * progress_blocks + "🔲" * (10 - progress_blocks)
        embed.add_field(name="🎴 Nọc Bài Tội Lỗi", value=f"Còn `{deck_size}` lá\n{progress_bar}", inline=True)
        
        # Bảng Log Cuộn
        log_text_arr = []
        for i, log in enumerate(self.logs):
            prefix = "🔴" if i == 0 else "⚪"
            log_text_arr.append(f"{prefix} {log}")
            
        log_text = "\n".join(log_text_arr)
        embed.add_field(name="📜 Lịch Sử Sinh Tử", value=f"```\n{log_text}\n```", inline=False)
        
        embed.set_footer(text="Quản Lý Bài: Chọn bài qua Nút bấm | Bốc Bài: Chấp nhận rủi ro!")
        
        file_attachment = None
        if self.last_played_card and self.last_action_player:
            file_attachment = MeoNoRenderer.create_hand_image(
                [self.last_played_card], 
                player_name=f"Vừa ném xuống bởi {self.last_action_player.display_name}"
            )
            if file_attachment:
                embed.set_image(url=f"attachment://{file_attachment.filename}")
                
        embeds = [embed]
        if notice_embed: embeds.append(notice_embed)
        
        attachments = [file_attachment] if file_attachment else []
        
        turn_changed = False
        if getattr(self, "_last_pinged_player", None) != self.current_player.id:
            turn_changed = True
            self._last_pinged_player = self.current_player.id

        if self.message: await self.message.edit(content=msg_header, embeds=embeds, view=self, attachments=attachments)

        if turn_changed:
            async def ghost_ping():
                try:
                    ping_msg = await self.message.channel.send(f"🔔 **TỚI LƯỢT RỒI:** {self.current_player.mention}, đến lượt bạn đánh bài hoặc bốc bài!")
                    await asyncio.sleep(4)
                    await ping_msg.delete()
                except: pass
            
            asyncio.create_task(ghost_ping())

    async def view_hand_callback(self, interaction: discord.Interaction):
        if self.is_game_over:
             return await interaction.response.send_message("❌ Ván bài này đã kết thúc!", ephemeral=True)
             
        if not self.lives[interaction.user.id]:
            return await interaction.response.send_message("🪦 Hồn ma thì đừng cố chạm vào bài...", ephemeral=True)
            
        player_hand = self.hands[interaction.user.id]
        if not player_hand:
            return await interaction.response.send_message("📭 Gió hú rỗng tuếch, trên tay bạn sạch bách!", ephemeral=True)
            
        file = MeoNoRenderer.create_hand_image(player_hand, interaction.user.display_name)
        
        view = HandInteractiveView(self, interaction.user.id)
        
        board_url = self.message.jump_url if self.message else ""
        board_link = f" \n🔗 **[Đến Bàn Cờ Chính của {self.owner.display_name}]({board_url})**" if board_url else ""
        msg = f"*Đây là quyền năng hiện hữu của bạn, {interaction.user.mention}*{board_link}\n🔥 HÃY LẠNH LÙNG PHÁN XÉT:"
        
        await interaction.response.send_message(content=msg, file=file, view=view, ephemeral=True)
        self.hand_interactions[interaction.user.id] = interaction

    async def draw_card_callback(self, interaction: discord.Interaction):
        await self.perform_draw(interaction, is_from_hand_view=False)
        
    async def perform_draw(self, interaction: discord.Interaction, is_from_hand_view=False):
        if getattr(self, "is_action_locked", False) or getattr(self, "_is_drawing", False):
            if is_from_hand_view: return await interaction.response.send_message("⏳ Bàn cờ đang bận xử lý, vui lòng đợi!", ephemeral=True)
            else: return await interaction.response.send_message("⏳ Bàn cờ đang bận, cấm Manh động!", ephemeral=True)
        
        self._is_drawing = True
        
        if is_from_hand_view:
            await interaction.response.defer()
        else:
            await interaction.response.defer(ephemeral=True)
            
        if interaction.user.id != self.current_player.id:
            self._is_drawing = False
            return await interaction.followup.send("⏳ Ai cho phép bạn cắt ngang số phận? Chờ đi!", ephemeral=True)
            
        card = self.deck.draw()
        if not card:
            self._is_drawing = False
            return await interaction.followup.send("📭 Hết bài thì huề cả làng?", ephemeral=True)
        
        try:
            if card.type == "exploding":
                if is_from_hand_view:
                    await interaction.edit_original_response(content="😱 **BẠN ĐÃ LẬT TRÚNG BÀI MÈO NỔ!!** Định mệnh đang gọi tên...", attachments=[], view=None)
                    msg_wait = None
                else:
                    msg_wait = await interaction.followup.send("😱 **BẠN ĐÃ LẬT TRÚNG BÀI MÈO NỔ!!** Định mệnh đang gọi tên...", ephemeral=True, wait=True)
                    
                suspense_embed = discord.Embed(title="🚨 BÁO ĐỘNG ĐỎ! MÈO NỔ ĐÃ BỊ KÍCH HOẠT! 🚨", description=f"**{interaction.user.display_name}** vừa lật trúng một quả bom!\nLiệu họ có sống sót hay tan xác...? *Đang kiểm tra Gỡ bom...*", color=0xFF0000)
                suspense_embed.set_image(url="https://media1.tenor.com/m/sPeb0hV4D5AAAAAd/bomb-explode.gif") 
                
                suspense_msg = await self.message.channel.send(content=interaction.user.mention, embed=suspense_embed)
                
                await asyncio.sleep(3.5)
                
                has_defuse = any(c.type == 'defuse' for c in self.hands[interaction.user.id])
                if has_defuse:
                    for c in self.hands[interaction.user.id]:
                        if c.type == 'defuse':
                            self.hands[interaction.user.id].remove(c)
                            break
                    self.deck.insert_randomly(card)
                    self.add_log(f"🔥 {interaction.user.display_name} đạp trúng MÈO NỔ nhưng đã ném lá DEFUSE kịp thời!")
                    self.next_turn()
                    
                    notice_embed = discord.Embed(title="🚨 CẢNH BÁO KHẨN: THOÁT CHẾT 🚨", description=f"**{interaction.user.display_name}** vừa gỡ bom thành công từ 1 hòm MÈO NỔ!", color=0x2ECC71)
                    success_embed = discord.Embed(title="✅ KHỬ BOM THÀNH CÔNG!", description=f"Oánh thót tim! **{interaction.user.display_name}** kịp vung lá Defuse khống chế Mèo Nổ và thoát chết trong gang tấc!", color=0x2ECC71)
                    await suspense_msg.edit(content=None, embed=success_embed)
                    
                    await self.update_board(notice_embed)
                    
                    if is_from_hand_view:
                        player_hand = self.hands[interaction.user.id]
                        file = MeoNoRenderer.create_hand_image(player_hand, interaction.user.display_name)
                        new_view = HandInteractiveView(self, interaction.user.id)
                        await interaction.edit_original_response(content="🛡️ **BẠN ĐÃ THOÁT NẠN!** Bạn bốc được Mèo Nổ nhưng Defuse đã tự động kích hoạt.", attachments=[file] if file else [], view=new_view)
                    else:
                        if msg_wait: 
                            try: await msg_wait.delete()
                            except: pass
                        msg = await interaction.followup.send("🛡️ **BẠN ĐÃ THOÁT NẠN!** Bạn bốc được Mèo Nổ nhưng Defuse đã tự động kích hoạt.", ephemeral=True, wait=True)
                        await asyncio.sleep(4)
                        try: await msg.delete()
                        except: pass
                else:
                    self.lives[interaction.user.id] = False
                    self.add_log(f"💥 BÙMM! {interaction.user.display_name} bốc nhầm MÈO NỔ và BANH XÁC!")
                    self.next_turn()
                    
                    notice_embed = discord.Embed(title="💥 BÙM! MỘT CHIẾN BINH NGÃ XUỐNG 💥", description=f"**{interaction.user.display_name}** vừa bốc ngay quả MÈO NỔ và tan xương nát thịt do thiếu Gỡ Bom!", color=0xE74C3C)
                    death_embed = discord.Embed(title="💥 BÙMM!! ĐÃ BANH XÁC!", description=f"Hết thuốc chữa! **{interaction.user.display_name}** chính thức bị Mèo Nổ thổi bay về cõi vĩnh hằng! 💀", color=0x000000)
                    await suspense_msg.edit(content=None, embed=death_embed)
                    
                    await self.update_board(notice_embed)
                    
                    if is_from_hand_view:
                        await interaction.edit_original_response(content="💥 **BÙMMM!** Không còn đường lui!", attachments=[], view=None)
                    else:
                        if msg_wait: 
                            try: await msg_wait.delete()
                            except: pass
                        msg = await interaction.followup.send("💥 **BÙMMM!** Không còn đường lui!", ephemeral=True, wait=True)
                        await asyncio.sleep(4)
                        try: await msg.delete()
                        except: pass
            else:
                self.hands[interaction.user.id].append(card)
                self.add_log(f"✌️ {interaction.user.display_name} đã bốc qua 1 khe cửa hẹp và hú vía an toàn.")
                self.next_turn()
                
                await self.update_board()
                
                if is_from_hand_view:
                    player_hand = self.hands[interaction.user.id]
                    file = MeoNoRenderer.create_hand_image(player_hand, interaction.user.display_name)
                    new_view = HandInteractiveView(self, interaction.user.id)
                    await interaction.edit_original_response(content=f"✅ Bốc xuất sắc! Bạn lĩnh được lá: **{card.name.upper()}**. Đã qua lượt.", attachments=[file] if file else [], view=new_view)
                else:
                    msg = await interaction.followup.send(f"✅ Bốc xuất sắc! Bạn lĩnh được lá: **{card.name.upper()}**", ephemeral=True, wait=True)
                    await asyncio.sleep(4)
                    try: await msg.delete()
                    except: pass
        finally:
            self._is_drawing = False

    def next_turn(self):
        curr_id = self.current_player.id
        if self.pending_turns[curr_id] > 1 and self.lives[curr_id]:
            self.pending_turns[curr_id] -= 1
            return 
            
        self.pending_turns[curr_id] = 0
        last = self.turn_queue.pop(0)
        self.turn_queue.append(last)
        while not self.lives[self.turn_queue[0].id]:
            dead = self.turn_queue.pop(0)
            self.turn_queue.append(dead)
            
        self.current_player = self.turn_queue[0]
        
        if self.pending_turns.get(self.current_player.id, 0) == 0:
            self.pending_turns[self.current_player.id] = 1
