# -*- coding: utf-8 -*-
"""FLOKTRON · texts of the messages. Add a language by copying the "en" block.
Tone: polite and businesslike — tasks are clear, no orders, not chummy."""

TEXTS = {
    "en": dict(
        hello="Good morning, {o}! Here are today's tasks:",
        due="due", letter="message",
        confirm="By 09:00 please confirm whether today works:",
        ok="✅ Accept", q="❓ I have a question", no="⛔ Not today",
        ok_body="✅ Accepted.", q_body="✍️ Question: ", no_body="✍️ Reason (optional): ",
        plus="+ Done", minus="− Did not work out",
        plus_body="✍️ What was done, next step: ", minus_body="✍️ What got in the way: ",
        ctx="Task", ctx_all="Tasks in this message:",
        evening="During the day:",
        task_note="After each task press its button. The task is at the top of the reply; write your answer at the very end, after ✍️ — one sentence is enough.",
        note="Each button opens a ready reply. Please keep the subject line — FLOKTRON recognises the answer by it.",
        subject="[{c} · {n}] {d} — tasks: {k}",
        e_hello="Good evening, {o}! How did today go? One button per task is enough:",
        e_subject="[{c} · {n}] {d} — evening",
        cal_title="Today in your calendar:",
        cal_file="The due dates of these tasks are attached as a calendar file (.ics) — one tap adds them to your calendar.",
    ),
    "lv": dict(
        hello="Labrīt, {o}! Šodienai sagatavoti šādi uzdevumi:",
        due="termiņš", letter="vēstule",
        confirm="Līdz 9:00 būtu labi saņemt apstiprinājumu, vai šodien sanāks:",
        ok="✅ Pieņemu", q="❓ Ir jautājums", no="⛔ Šodien nesanāks",
        ok_body="✅ Pieņemu.", q_body="✍️ Jautājums: ", no_body="✍️ Iemesls (ja vēlaties): ",
        plus="+ Izdevās", minus="− Neizdevās",
        plus_body="✍️ Kas izdevās, nākamais solis: ", minus_body="✍️ Kas traucēja: ",
        ctx="Uzdevums", ctx_all="Uzdevumi šajā vēstulē:",
        evening="Dienas laikā:",
        task_note="Pēc katra uzdevuma var nospiest tā pogu. Augšā būs uzdevums, atbildi var uzrakstīt pašās beigās — aiz zīmes ✍️; pietiek ar vienu teikumu.",
        note="Katra poga atver gatavu atbildi. Lūdzu, nemainiet tēmu — pēc tās FLOKTRON atpazīst atbildi.",
        subject="[{c} · {n}] {d} — uzdevumi: {k}",
        e_hello="Labvakar, {o}! Kā šodien gāja? Pietiek ar vienu pogu katram uzdevumam:",
        e_subject="[{c} · {n}] {d} — vakars",
        cal_title="Šodien kalendārā:",
        cal_file="Šo uzdevumu termiņi pievienoti kā kalendāra fails (.ics) — ar vienu pieskārienu tos var ielikt savā kalendārā.",
    ),
    "ru": dict(
        hello="Доброе утро, {o}! На сегодня подготовлены такие задачи:",
        due="срок", letter="письмо",
        confirm="До 09:00 будет удобно получить подтверждение, получится ли сегодня:",
        ok="✅ Принимаю", q="❓ Есть вопрос", no="⛔ Сегодня не получится",
        ok_body="✅ Принимаю.", q_body="✍️ Вопрос: ", no_body="✍️ Причина (по желанию): ",
        plus="+ Сделано", minus="− Не вышло",
        plus_body="✍️ Что получилось, следующий шаг: ", minus_body="✍️ Что помешало: ",
        ctx="Задача", ctx_all="Задачи в этом письме:",
        evening="В течение дня:",
        task_note="После каждой задачи можно нажать её кнопку. Вверху ответа будет задача, ответ — в самом конце, после ✍️; достаточно одной фразы.",
        note="Каждая кнопка открывает готовый ответ. Тему письма лучше не менять — по ней FLOKTRON узнаёт ответ.",
        subject="[{c} · {n}] {d} — задач: {k}",
        e_hello="Добрый вечер, {o}! Как прошёл день? Достаточно одной кнопки на задачу:",
        e_subject="[{c} · {n}] {d} — вечер",
        cal_title="Сегодня в календаре:",
        cal_file="Сроки этих задач приложены файлом календаря (.ics) — одно касание, и они в вашем календаре.",
    ),
}


def texts(lang):
    return TEXTS.get(str(lang or "en").strip().lower(), TEXTS["en"])
