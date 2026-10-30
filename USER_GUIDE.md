# FreshQueue - Istemal ka tareeqa (step by step example)

Is guide mein ek farzi dukaan **"Ali General Store"** ka din shuru se aakhir tak chalaya gaya hai.
Har step ke saath likha hai ke **kya dabana hai** aur **screen pe kya aana chahiye**. Ye saare nateeje asal program
chala ke check kiye gaye hain. (Tareekhein tumhari aaj ki date ke hisaab se badal jayengi, baqi sab wahi rahega.)

---------------------------------------------------------------------------------------------------

## 0. Program kholna
1. **Zip ko NAYE khali folder mein Extract All karo** (purane FreshQueue folder ke upar kabhi nahi, warna purani files mil jati hain aur compile fail hota hai). Phir folder `FreshQueue_v2` kholo aur **`run.bat`** pe double-click karo.
2. Pehli dafa 5-10 second lagte hain (Java files khud compile hoti hain). Phir program khul jata hai.
3. Shuru mein list **khali** hoti hai: "No stock added yet".

> Chalane ke liye Java (JDK 11+) aur Python (3.8+) install hona chahiye. Koi pip package nahi chahiye.

---------------------------------------------------------------------------------------------------

## 1. Subah: dukaan ka maal daalna (Create = enqueue)

**Practice ke liye jaldi:** khali list mein button **"Load practice items"** dabao. 5 cheezein aa jayengi:

| ID | Naam | Kitne | Qeemat | Expiry |
|---|---|---|---|---|
| 101 | Fresh Milk 1L | 60 | 290 | aaj se 2 din baad |
| 102 | Bread Loaf | 35 | 150 | 3 din baad |
| 103 | Yogurt 500g | 48 | 210 | 6 din baad |
| 104 | Orange Juice | 40 | 320 | 45 din baad |
| 105 | Basmati Rice 5kg | 90 | 1650 | 240 din baad |

**Screen pe dekho:**
- Upar 4 dabbe: Items in stock = **5**, Total pieces = **273**, Expiring in 7 days = **3**, Running low = **0**.
- Upar narangi patti: "3 item(s) will expire within 7 days - sell them first!"
- Table mein sab se upar **"1 SELL FIRST"** = Fresh Milk. Ye sab se pehle aaya tha, isay pehle bechna hai.

**Ab naya maal add karo** (doodh ka dusra batch aaya):
1. **"+ Add New Stock"** dabao.
2. Item name: `Fresh Milk 1L` | Type: `Dairy` | How many: `40` | Price: `300` | Expiry: 10 din baad ki koi tareekh.
3. **Save** dabao.

**Nateeja:** list mein 6 items, Fresh Milk ka naya batch sab se **neeche (REAR)** laga. Total pieces = **313**.
Naya maal hamesha line ke aakhir mein lagta hai - yahi **enqueue** hai.

---------------------------------------------------------------------------------------------------

## 2. Din mein: sale likhna (FIFO)

Ek customer ne **70 piece doodh** liya.
1. **"Record a Sale"** dabao.
2. "Which item was sold?" mein `Fresh Milk 1L (100)` chuno. Bracket mein 100 isliye ke dono batch mila ke 100 piece hain.
3. "How many pieces?" mein `70` likho. **Record Sale** dabao.

**Screen pe aana chahiye:**
```
Sold 70 x Fresh Milk 1L  =  Rs 20,400
   Batch #101: 60 pieces taken  (this batch is now finished)
   Batch #106: 10 pieces taken
```
**Ye kaise hua?** Program ne pehle **purane batch (#101)** ke saare 60 piece liye (60 x 290 = 17,400). Wo khatam ho gaya
to list se hat gaya. Baqi 10 piece **naye batch (#106)** se liye (10 x 300 = 3,000). Total 20,400.
Yahi **FIFO** hai: jo pehle aaya, wo pehle bika.

Ab list dekho: Milk ka purana batch gayab hai, naye batch mein **30** piece bache hain.

**Galti try karo:** dobara "Record a Sale", doodh, `99` likho. Program rokega:
"Only 30 piece(s) of 'Fresh Milk 1L' can be sold. You asked for 99." (Zyada bechna mumkin nahi.)

---------------------------------------------------------------------------------------------------

## 3. Counter pe line (Customer Line tab)

Tab **"Customer Line"** kholo.
1. Naam `Ali` likho aur **"Customer Joined the Line"** dabao (Enter bhi chalta hai). Phir `Sara`, phir `Usman`.
2. **Nateeja:** People waiting = **3**. Neeche line mein Ali (NEXT), Sara, Usman. Token #1, #2, #3.
3. **"Call Next Customer"** dabao. **Nateeja:** NOW SERVING = `#1 Ali`, People waiting = **2**, ab NEXT = Sara.

Line mein jo pehle aaya wo pehle serve hua - ye queue ka sab se aam example hai.
(Is tab ki line program band karne pe khatam ho jati hai; stock aur sales save rehti hain.)

---------------------------------------------------------------------------------------------------

## 4. Hisaab: Sales History tab
Tab **"Sales History"** kholo.
- Sales today = **20,400**, Pieces sold today = **70**, Sales kept = **1 / 50**.
- Table mein doodh ki sale (sab se nayi upar).
- Program sirf aakhri **50 sales** rakhta hai. 51vi sale aaye to sab se purani hat jati hai (ye bhi ek queue hai).

---------------------------------------------------------------------------------------------------

## 5. Shaam: expire aur kam stock

1. Stock tab pe **"+ Add New Stock"**: Name `Old Cream`, How many `5`, Price `100`, Expiry: **3 din pehle ki tareekh**. Save.
2. **Nateeja:** laal patti "1 item(s) have EXPIRED...", Running low = **1** (5 piece, 10 se kam), Old Cream laal rang mein "EXPIRED".
   Expire maal ki sale nahi ho sakti (Record a Sale mein ye maal nazar nahi aata).
3. **"Remove Expired"** dabao, Yes. Old Cream hat gaya, laal patti gayab.

Baqi buttons:
- **Edit Selected** (ya row pe double-click): pehle row chuno, phir ye. Qeemat/quantity badal sakte ho.
- **Remove Selected**: koi bhi chuni hui cheez hatao.
- **Oldest Stock Finished**: sab se upar wala maal khatam ho gaya, hata do (ye seedha **dequeue** hai).
- **Search**: naam likhte hi list filter ho jati hai.

---------------------------------------------------------------------------------------------------

## 6. Sir ko dikhane ke liye (Teacher view)
Upar right pe **"How the Queue works"** dabao.
- **Stock tab:** neeche boxes mein queue dikhti hai (FRONT se REAR tak) aur **log** dikhata hai ke har kaam mein kitni
  `enqueue` aur `dequeue` calls lagin. Misal: sale ke baad likha hoga `used 11 enqueue + 12 dequeue calls`.
  Dekho: sale ke liye **poori queue 2 baar ghoomi**, kyunke queue mein beech ka item seedha nahi milta.
- **Customer Line tab:** line ke neeche "Last action: dequeued Ali ... (0 enqueue + 1 dequeue)".
- Naya tab **"Speed Test (Teacher)"**: **Run Speed Test** dabao (kuch second lagte hain). Table aur 2 chart aate hain:
  - Add / Remove first / Peek **seedhi lakeer** = bade ya chhote queue mein same waqt = **O(1)**.
  - Search / Edit / Remove chosen **barhti lakeer** = queue jitni bari, utna slow = **O(n)**.
  - Neeche program khud likhta hai ke nateeja kya hai. **Save results (CSV)** se Excel ke liye file ban jati hai.
  - Nateeje har computer pe thore alag aate hain. Report mein **apne computer ke** nateeje aur screenshot lagana.

**Roman Urdu / English:** upar right wale button se poora program ek click mein badal jata hai.

---------------------------------------------------------------------------------------------------

## 7. Code kahan hai? (viva ke liye)
| Kaam | File |
|---|---|
| Queue khud ki (enqueue, dequeue, peek) | `backend/LinkedQueue.java`, `backend/Node.java` |
| Stock ke CRUD, FIFO sale, expire hatana | `backend/InventoryManager.java` |
| Customer line / Sales history (2 aur queues) | `backend/CustomerLine.java`, `backend/SalesHistory.java` |
| Speed test | `backend/Benchmark.java` |
| Java ka "darwaza" (Python se baat) | `backend/Server.java` |
| Screens, buttons | `frontend/app.py` |
| Python se Java ko request | `frontend/api.py` |
| Screen ke alfaaz (English / Roman Urdu) | `frontend/texts.py` |

**Java aur Python kaise baat karte hain:** Python program Java ko khud start karta hai. Dono computer ke andar hi
`127.0.0.1` pe chhote messages (HTTP) bhejte hain. Python sirf screen dikhata hai; queue aur saari logic Java mein hai.

## 8. Viva mein ye sawal aa sakte hain
1. **Queue hi kyun?** Doodh/bread jaisa maal batch mein aata hai, aur pehle aane wala pehle bikna chahiye warna purana expire ho jata hai. Ye FIFO hai.
2. **Queue khud kyun banayi, `java.util.Queue` kyun nahi?** DSA mein hume andar ka kaam dikhana hai: linked nodes, front aur rear pointers.
3. **Enqueue / dequeue / peek ka time?** Teeno **O(1)**: sirf front ya rear pointer chhua jata hai.
4. **Search / edit / remove-by-choice ka time?** **O(n)**. Queue mein beech ka item seedha nahi milta, is liye hum "rotate" karte hain: har item ko dequeue karke wapas enqueue.
5. **Rotate karne se order kharab kyun nahi hota?** Hum bilkul `size` baar nikalte aur usi tarteeb mein wapas lagate hain, to queue pehle jaisi ho jati hai.
6. **Queue ki kamzori kya hai?** Beech tak pahunchna slow hai. Speed Test chart isi ka saboot hai.
7. **Sale mein queue kaise use hui?** Pehli rotation se check kiya ke maal kaafi hai; doosri rotation mein purane batch se maal kaata, khatam hone wale batch ko wapas enqueue nahi kiya.
8. **Sales history ko 50 pe kyun roka?** Bounded queue: 51vi sale pe pehle dequeue (sab se purani), phir enqueue. Memory control mein rehti hai.

## 9. Agar program na khule
- **"could not start its engine"** = error box ke neeche "Reason" likha hota hai, wohi asli wajah hai (copy karke bhej do). Ye `data\startup_error.txt` mein bhi save hota hai. Aam wajah: purane folder ke upar extract kiya (naya khali folder use karo), ya JDK/Java PATH mein nahi.
- **Python ka error "No module named tkinter"** = Python dobara python.org se install karo aur "tcl/tk" option tick rakho.
- Data `data` folder mein save hota hai. Sab kuch naye sire se shuru karna ho to program band karke `data` folder delete kar do.

---

## New in v3: Themes, Dark mode, Languages, Scrollbar

- **Theme button (top bar)**: pick one of 6 looks: Green, Ocean, Sunset, Purple (light) and Night, Midnight (dark).
- **Night mode / Light mode button**: one click switches between dark and light. It remembers your last light and last dark theme.
- **Language button**: English, Roman Urdu, Urdu (اردو), Sindhi (سنڌي), Arabic (العربية). Urdu, Sindhi and Arabic flip the screen right-to-left.
- Your choices are saved in `data/settings.json` and come back next time.
- **Speed Test (teacher view)** now has a scrollbar on the right (mouse wheel works too), so both graphs and the conclusion are fully visible. This page is always in English.
- Optional, only if Arabic-script letters look broken on Mac/Linux: `pip install arabic-reshaper python-bidi`. On Windows nothing is needed.
