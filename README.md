# MÈO NỔ (EXPLODING KITTENS) - STANDALONE COMPONENT

Thư mục này đóng gói riêng toàn bộ game Mèo Nổ (Exploding Kittens):

1. **`meono.py`**:
   - Chứa logic game Discord (View, Button, Select, Flow xử lý ván đấu Mèo Nổ).
   - Chứa class `MeoNoRenderer` (Vẽ bài trên tay hình quạt xòe bằng Pillow).

2. **`meono_logic.py`**:
   - Chứa logic chia bài, danh sách thẻ bài (`Card`), bộ bài nọc (`Deck`).
   - Xử lý các lá bài Mèo thường, Attack, Skip, Favor, Shuffle, See the Future, Nope, Defuse, Mèo Nổ.

3. **`image_meono/`**:
   - Thư mục chứa toàn bộ 56 ảnh thẻ bài chất lượng cao gốc phục vụ cho việc render bài trên tay người chơi.
