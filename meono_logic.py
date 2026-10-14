import random

class Card:
    def __init__(self, card_type, name, image_name):
        self.type = card_type
        self.name = name
        self.image_name = image_name
    
    def __repr__(self):
        return f"{self.name}"
        
    def to_dict(self):
        return {
            "type": self.type,
            "name": self.name,
            "image": self.image_name
        }

class Deck:
    def __init__(self, num_players):
        self.cards = []
        self.num_players = num_players
        self.build_deck()
    
    def build_deck(self):
        # Tạo bài cơ bản (trừ Mèo nổ và Defuse)
        
        # Mèo thường (Dùng cho combo 2 lá, 3 lá, 5 lá)
        cat_cards = [
            ('cat', 'Taco Cat', 'tacocat', 4),
            ('cat', 'Cattermelon', 'cattermelon', 4),
            ('cat', 'Hairy Potato Cat', 'hairypotatocat', 4),
            ('cat', 'Beard Cat', 'beardcat', 4),
            ('cat', 'Rainbow-Ralphing Cat', 'rainbowcat', 4)
        ]
        
        # Bài chức năng
        action_cards = [
            ('nope', 'Nope', 'nope', 5),
            ('attack', 'Attack', 'attack', 4),
            ('skip', 'Skip', 'skip', 4),
            ('favor', 'Favor', 'favor', 4),
            ('shuffle', 'Shuffle', 'shuffle', 4),
            ('future', 'See the Future', 'future', 5)
        ]
        
        for c_type, c_name, prefix, count in cat_cards + action_cards:
            for i in range(count):
                self.cards.append(Card(c_type, c_name, f"{prefix}_{i+1}.png"))
                
        random.shuffle(self.cards)
        
    def deal(self):
        # Lấy danh sách Defuse và Exploding Kittens (tối đa lấy đúng sl cần)
        defuse_pool = [Card('defuse', 'Defuse', f'defuse_{i+1}.png') for i in range(6)]
        random.shuffle(defuse_pool)
        
        exploding_pool = [Card('exploding', 'Mèo Nổ', f'kitten_{i+1}.png') for i in range(4)]
        random.shuffle(exploding_pool)

        # Chia mỗi người 4 lá ngẫu nhiên và 1 lá Defuse
        hands = []
        for _ in range(self.num_players):
            hand = [defuse_pool.pop()]
            for _ in range(4):
                hand.append(self.cards.pop())
            hands.append(hand)
            
        # Thêm Mèo Nổ (Số người chơi - 1)
        for _ in range(self.num_players - 1):
            self.cards.append(exploding_pool.pop())
            
        # Thêm Defuse thừa (Defuse tổng là 6, do đã lấy chia mỗi người 1 lá, phần còn lại trong defuse_pool)
        for card in defuse_pool:
             self.cards.append(card)
             
        random.shuffle(self.cards)
        return hands
        
    def draw(self):
        if not self.cards:
            return None
        return self.cards.pop()

    def insert_randomly(self, card):
        # Chèn thẻ bài vào vị trí ngẫu nhiên trong nọc
        idx = random.randint(0, len(self.cards))
        self.cards.insert(idx, card)
