# Loomin-Docs — verification & detailed query / “answer” evidence

## Important: retrieval vs chat “answers”

| Layer | What it is |
|-------|------------|
| **This document** | Results from **`POST /api/rag/search`** — the **retrieved text chunks** the backend would inject into the LLM. |
| **Assistant chat (`POST /api/chat`)** | Ollama **generates** a natural-language answer **from** those chunks + system instructions + citations. |
| **“Answer (from corpus only)”** below | A **human summary** of what the **top retrieved chunk** supports — the same facts the model is expected to use when RAG is on. |

Automated scripts check that **expected keywords** appear in the **merged top‑k** chunks (not only in rank #1). Timings (`retrieval_time_ms`) **vary by machine**; excerpts match indexed **`Luna_the_Dream_Keeper.pdf`** and **`Kai_and_the_Guardian_Realm.pdf`**.

---

## Project status (core deliverable)

| Goal | Status |
|------|--------|
| Collaborative editor + AI sidebar | Implemented |
| RAG (FAISS + hybrid BM25) over uploads | Implemented |
| Citations + SQLite + Ollama | Implemented |
| Air-gap bootstrap story | `setup.sh`, `deploy/*`, README |
| Faithfulness smoke test | `test_rag.py` |

**Interviewers / graders:** open **`README.md`** and scroll to **“For interviewers & evaluators”**. That section explains **which option to run** (networked vs air-gap), **what is and is not in Git** (RPMs / image tarballs assembled per **`deploy/bootstrap/PACKAGE_MANIFEST.md`**), **safety and ports**, a **pre-flight checklist** for **Option C**, and an **evaluator checklist** so the stack can be brought up **completely and predictably**.

---

## Suite summary (exit code 0 = PASS)

| Script | Checks | Result |
|--------|--------|--------|
| `scripts/multi_query_rag_test.py` | 8 | **8/8 OK** |
| `scripts/targeted_rag_checks.py` | 6 | **6/6 OK** |
| `scripts/complex_rag_tests.py` | 6 | **6/6 OK** |
| `test_rag.py` (`SKIP_OLLAMA=1`, in container) | fixture | **PASS** |
| `GET /health` | — | `{"status":"ok"}` |

---

## A. `multi_query_rag_test.py` (Luna, top‑k = 4)

### 1. Mr. Whiskers / stuffed toy

- **Query:** `Who is Mr. Whiskers or Emma's stuffed toy?`
- **Answer (from corpus only):** Mr. Whiskers is Emma’s **favorite stuffed rabbit**; she sleeps with him tucked under her arm.
- **API:** `retrieval_time_ms` ≈ 14–240 (varies); **top chunk** `Luna_the_Dream_Keeper:fffcb02c:1`, score ≈ `0.0328`, file `Luna_the_Dream_Keeper.pdf`.
- **Top retrieved chunk (excerpt):**

> Chapter 1: The Girl in the Moonlit Room Once upon a time, in a cozy cottage at the edge of an enchanted forest, there lived a young girl named Emma. She had long golden curls and the brightest blue eyes you ever did see. Every night, when the moon rose high in the sky, Emma would snuggle into her soft bed with her favorite stuffed rabbit, Mr. Whiskers, tucked under her arm. But Emma had a special gift that most children didn't have—she could see things others couldn't. On this particular night, as Emma was just about to close her eyes, something magical happened. A soft, shimmering light appeared at the foot of her bed, casting long shadows of silver and blue across the room. Emma wasn't frightened. Instead, she felt a warm, peaceful feeling wash over her, like being wrapped in the softest cloud.

### 2. Dream Jar

- **Query:** `What is the Dream Jar made of and what is inside?`
- **Answer (from corpus only):** The Dream Jar is made of **pure crystal**. **Inside** are **children’s dreams** from around the world (swirling colors; Luna explains it in Chapter 3).
- **Top chunk:** `Luna_the_Dream_Keeper:fffcb02c:5`, score ≈ `0.0328`.
- **Top retrieved chunk (excerpt):**

> Chapter 3: The Crystal Dream Jar Luna reached into the folds of her moonbeam dress and pulled out the most exquisite object Emma had ever laid eyes upon. It was a jar made of pure crystal, filled with swirling colors—soft pinks, gentle blues, and golden yellows that danced and twirled like miniature auroras. 'This is my Dream Jar,' Luna explained, holding it up to catch the light. 'Inside are dreams from children just like you from all over the world. Some dream of flying with dragons, others dream of exploring underwater kingdoms, and many dream of friendship and adventure.' 'But there is always room for more,' Luna continued with a mysterious smile. 'And I was wondering, dear Emma, if you would like to share one of your dreams with me tonight. But first, let me tell you about my special friends who help me protect these precious dreams.'

### 3. Unicorn and owl

- **Query:** `Name the unicorn and the owl that help Luna.`
- **Answer (from corpus only):** **Stardust** the unicorn and **Whisper** the wise owl (with Shimmer the phoenix also present in the same passage).
- **Top chunk:** `Luna_the_Dream_Keeper:fffcb02c:36`.
- **Top retrieved chunk (excerpt):**

> her bed. This time, Luna was not alone. She had brought Stardust the unicorn with her, and Whisper the wise owl, and Shimmer the glowing phoenix. 'We wanted to visit you again, dear Emma,' Luna said, 'because you have spread the magic of dreams to others by sharing your joy and kindness. And when you do that, you help me protect the dreams of all the children in the world.'

### 4. Shimmer

- **Query:** `What is Shimmer?`
- **Answer (from corpus only):** Shimmer is a **tiny phoenix** made of **soft, glowing light**; she comforts children before sleep.
- **Top chunk:** `Luna_the_Dream_Keeper:fffcb02c:8`.
- **Top retrieved chunk (excerpt):**

> there is Shimmer, a tiny phoenix who never sleeps. She is made entirely of soft, glowing light and leaves trails of comfort wherever she flies. Children all around the world feel her warmth right before they drift off to sleep.' Emma felt her eyes growing heavy just hearing about these wonderful creatures, but she wanted to hear more.

### 5. Where Emma lives

- **Query:** `Where does Emma live? Cottage forest moonlit`
- **Answer (from corpus only):** Emma lives in a **cozy cottage** at the edge of an **enchanted forest** (moonlit nights in the same chapter).
- **Top chunk:** `Luna_the_Dream_Keeper:fffcb02c:1`, score ≈ `0.0323`.
- **Top retrieved chunk:** same long Chapter 1 excerpt as in **§1** (cottage + forest + blue eyes + Mr. Whiskers).

### 6. Emma’s eyes

- **Query:** `What color are Emma's eyes?`
- **Answer (from corpus only):** **Blue** — “the brightest **blue eyes**”.
- **Top chunk:** `Luna_the_Dream_Keeper:fffcb02c:1`, score ≈ `1.028` (dense + lexical agreement).
- **Top retrieved chunk:** same Chapter 1 excerpt as **§1** (contains “brightest blue eyes”).

### 7. Luna and her title

- **Query:** `Who is Luna and her title?`
- **Answer (from corpus only):** **Luna** introduces herself as the **Dream Keeper** (fairy who collects children’s dreams). *Note:* Rank‑1 chunk is often Chapter 3 (Dream Jar); **“Dream Keeper”** and **Luna** also appear in other top‑4 chunks (e.g. Chapter 2). Scripts require both phrases in **merged** top‑4.
- **Top chunk (rank 1):** `Luna_the_Dream_Keeper:fffcb02c:5` — Dream Jar dialogue (identifies Luna by name).
- **Top retrieved chunk (excerpt):**

> Chapter 3: The Crystal Dream Jar Luna reached into the folds of her moonbeam dress and pulled out the most exquisite object Emma had ever laid eyes upon. It was a jar made of pure crystal, filled with swirling colors—soft pinks, gentle blues, and golden yellows that danced and twirled like miniature auroras. 'This is my Dream Jar,' Luna explained, holding it up to catch the light. 'Inside are dreams from children just like you from all over the world. …

### 8. Publishing / title page

- **Query:** `Illustrated by or publishing on the title page?`
- **Answer (from corpus only):** The title material is associated with **Sweet Dreams Publishing** (“Illustrated by Sweet Dreams Publishing”).
- **Top chunk:** `Luna_the_Dream_Keeper:fffcb02c:0`.
- **Top retrieved chunk (full short chunk):**

> [Title & opening] I LUNA THE DREAM KEEPER I A Magical Bedtime Story Where Dreams Come True... Illustrated by Sweet Dreams Publishing

---

## B. `targeted_rag_checks.py` (Luna + Kai, top‑k = 6)

### B1. Sweet Dreams Publishing

- **Query:** `Sweet Dreams Publishing illustrated by`
- **Answer (from corpus only):** Title / imprint: **Sweet Dreams Publishing** on the Luna story opening.
- **Top chunk:** `Luna_the_Dream_Keeper:fffcb02c:0` — same title line as **§A8**.

### B2. Cottage and enchanted forest

- **Query:** `Where does Emma live? cozy cottage edge of an enchanted forest`
- **Answer (from corpus only):** **Cozy cottage** at the edge of an **enchanted forest**.
- **Top chunk:** `Luna_the_Dream_Keeper:fffcb02c:1` — Chapter 1 excerpt as in **§A1**.

### B3. Emma’s eyes (phrase check)

- **Query:** `What color are Emma's eyes?`
- **Answer (from corpus only):** **Blue eyes** in Chapter 1.
- **Top chunk:** `Luna_the_Dream_Keeper:fffcb02c:1`.

### B4. Kai — attic object

- **Query:** `What object did Kai find in the attic?`
- **Answer (from corpus only):** An old **leather journal** (glowing, symbols on cover).
- **Top chunk:** `Kai_and_the_Guardian_Realm:5f2603a9:2`, file `Kai_and_the_Guardian_Realm.pdf`.
- **Top retrieved chunk (excerpt):**

> completely alert. This wasn't scary—it was fascinating. He grabbed his flashlight and crept closer to the mysterious light. As his eyes adjusted, Kai realized the light was coming from an old leather journal he'd found in the attic weeks ago but never opened. It was glowing with an otherworldly sheen, and strange symbols were etched across its cover.

### B5. Kai’s eyes

- **Query:** `What color are Kai's eyes?`
- **Answer (from corpus only):** The automated test requires **`green`** and **`eyes`** somewhere in **all top‑6** chunks. **Rank‑1** may be a metaphorical “trust your hearing / eyes” scene; **other ranks** in the six chunks carry the literal **green eyes** wording from the Kai PDF. (Hybrid retrieval still **PASS**.)
- **Top chunk (rank 1):** `Kai_and_the_Guardian_Realm:5f2603a9:11`.
- **Top retrieved chunk (excerpt):**

> illusions flickered everywhere—false paths, phantom creatures, and impossible landscapes. 'How are we supposed to find the Stone in this chaos?' Kai wondered aloud. Immediately, his voice echoed back: 'chaos... chaos... chaos...' Nightwhisper approached Kai and said quietly, 'The secret is not to rely on your eyes. Listen instead. Real echoes follow patterns. Trust what you hear, not what you see.' Kai closed his eyes and focused. …

### B6. Theron

- **Query:** `Who is Theron and what is his title?`
- **Answer (from corpus only):** **Theron** is the **Guardian of Stories** (and Keeper of the Realm’s Ancient Secrets).
- **Top chunk:** `Kai_and_the_Guardian_Realm:5f2603a9:4`.
- **Top retrieved chunk (excerpt):**

> are you?' he asked, his voice steady despite his racing pulse. 'And what is the Guardian Realm?' 'I am Theron, the Guardian of Stories and Keeper of the Realm's Ancient Secrets,' the voice replied. 'The Guardian Realm is a hidden world that exists alongside your own, filled with creatures of incredible power and wisdom. It is protected by an ancient balance that keeps both worlds in harmony. But now, that balance is being threatened.'

---

## C. `complex_rag_tests.py`

### C1. Cross-doc Luna vs Kai

- **Query:** `Compare Luna and Kai: who is the fairy vs who is the boy with the journal?`
- **Answer (from corpus only):** **Luna** is described as a **fairy** / **Dream Keeper** (Luna PDF). **Kai** is the boy tied to the **leather journal** (Kai PDF). The test checks **luna**, **kai**, and **journal** appear in **merged** top‑6.
- **Top chunk (rank 1):** `Luna_the_Dream_Keeper:fffcb02c:3`.
- **Top retrieved chunk (excerpt):**

> Chapter 2: Luna Appears Out of the light stepped the most beautiful creature Emma had ever seen. She was a delicate fairy with translucent wings that sparkled like diamonds in the moonlight. Her skin glowed with a soft, silvery sheen, and her dress was made of flowing moonbeams and starlight. … 'My name is Luna, and I am the Dream Keeper. …'

### C2. Title line (BM25-friendly)

- **Query:** `Sweet Dreams Publishing title page illustrator`  
- **Evidence:** same as **§A8 / §B1**.

### C3. Packed Emma facts

- **Query:** `Emma cottage enchanted forest golden curls blue eyes Mr Whiskers`  
- **Answer (from corpus only):** Chapter 1 bundles **Emma**, **cottage**, **enchanted forest**, **golden curls**, **blue eyes**, **Mr. Whiskers** (stuffed rabbit).  
- **Top chunk:** `Luna_the_Dream_Keeper:fffcb02c:1` — Chapter 1 long excerpt.

### C4. Theron + Guardian Realm

- **Query:** `Theron Guardian of Stories Chronicle Guardian Realm balance threatened`  
- **Top chunk:** `Kai_and_the_Guardian_Realm:5f2603a9:3` — Chapter 2 journal + Theron introduction (longer excerpt includes Chronicle, Theron, balance threatened).
- **Top retrieved chunk (excerpt):**

> Chapter 2: The Ancient Journal Kai carefully picked up the journal. … 'I am Theron, the Guardian of Stories and Keeper of the Realm's Ancient Secrets,' the voice replied. 'The Guardian Realm is a hidden world … It is protected by an ancient balance … But now, that balance is being threatened.'

### C5. Dream Guardians entities

- **Query:** `Stardust unicorn Whisper owl Shimmer phoenix Dream Guardians`  
- **Answer (from corpus only):** Chapter 4 lists **Stardust** (unicorn), **Whisper** (owl), **Shimmer** (phoenix) as **Dream Guardians**.
- **Top chunk:** `Luna_the_Dream_Keeper:fffcb02c:7`.
- **Top retrieved chunk (excerpt):**

> Chapter 4: The Dream Guardians Luna began to describe the magical friends she traveled with throughout the night. 'First, there is Stardust, a magnificent white unicorn … He helps guide me through the darkness and keeps the dreams safe.' … 'Then there is Whisper, a wise old owl with golden eyes. …' 'And finally, there is Shimmer, a tiny phoenix who never sleeps. …'

### C6. Negative probe (Harry Potter)

- **Query:** `What is NOT in the story: Harry Potter Hogwarts`
- **Expected behavior:** Retrieved chunks should **not** introduce **Harry Potter** / **Hogwarts**; they should stay on **Luna/Kai** corpus. **Result: OK** (no forbidden substrings in merged retrieval).
- **Top chunk (rank 1):** `Luna_the_Dream_Keeper:fffcb02c:37` — closing chapter on Dream Keepers / sleep / belief (unrelated to HP).
- **Top retrieved chunk (excerpt):**

> Chapter 19: The Promise Forever As the story of Emma and Luna continues, night after night, readers should know that this same magic exists for every child who believes. Every night, when you close your eyes and drift off to sleep, there are Dream Keepers working to fill your mind with wonder and your heart with peace. …

---

## D. `test_rag.py` (assessment faithfulness script)

- **Fixture:** `fixtures/sample_corpus.txt` (ingested into a temp `DATA_DIR`).
- **Question:** e.g. codename and region for the Loomin project (see script).
- **With `SKIP_OLLAMA=1`:** PASS if **LOOMIN-7** and **Arctic** appear in **retrieved** chunks (retrieval-only).
- **Without `SKIP_OLLAMA`:** additionally checks Ollama answer tokens overlap retrieved text (heuristic).

---

## Regenerate evidence from your machine

After `docker compose up` and PDF upload:

```bash
python3 scripts/dump_rag_evidence.py
python3 scripts/dump_rag_evidence.py http://127.0.0.1:8000   # optional base URL
```

Full scripted run + log: `./scripts/run_assessment_verification.sh` → `assessment-run.log`.

---

## Assessment crosswalk

See **`README.md` → “Deliverables vs project-assesment.md”**. Bootstrap binary bundle: **`deploy/bootstrap/PACKAGE_MANIFEST.md`**.
