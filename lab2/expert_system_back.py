import os
import tkinter as tk
from tkinter import messagebox, simpledialog

RULES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules.txt")

class Rule:
    def __init__(self, conditions, conclusion, text):
        self.conditions = conditions  # список условий [(объект, значение), ...]
        self.conclusion = conclusion  # вывод (объект, значение)
        self.text = text              # исходный текст правила


def pair(text):
    """'тесто=дрожжевое' -> ('тесто', 'дрожжевое')"""
    obj, val = text.split("=", 1)
    return (obj.strip(), val.strip())


def line_in_rule(line):
    """Одна строка файла -> объект Rule (или None, если строка не правило)."""
    line = line.strip()
    if not line or "ЕСЛИ" not in line or "ТО" not in line:
        return None
    after_if = line.split("ЕСЛИ", 1)[1]
    cond_part, concl_part = after_if.rsplit("ТО", 1)
    conditions = [pair(p) for p in cond_part.split(" И ") if p.strip()]
    return Rule(conditions, pair(concl_part), line)


def load_rules(path):
    rules = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for raw_line in f:
                rule = line_in_rule(raw_line)
                if rule is not None:
                    rules.append(rule)
    return rules


def save_rules(path, rules):
    with open(path, "w", encoding="utf-8") as f:
        for rule in rules:
            f.write(rule.text + "\n")


# ---------- 2. ОБРАТНАЯ ЦЕПОЧКА РАССУЖДЕНИЙ ----------
def prove(goal, rules, facts, log, ask_func, stack, depth=0):
    """
    Пытается доказать цель goal = (объект, значение).
    Возвращает True (доказана) или False (не доказана).
    facts    - рабочая база данных {объект: значение}
    stack    - цели, которые доказываем прямо сейчас (защита от зацикливания)
    depth    - глубина рекурсии (нужна только для отступов в журнале)
    """
    obj, val = goal
    pad = "    " * depth
    log("{}Цель: {} = {}".format(pad, obj, val))

    # Шаг 1. Объект уже есть в базе фактов?
    if obj in facts:
        if facts[obj] == val:
            log("{}  + это известный факт".format(pad))
            return True
        log("{}  - в базе {} = {}, а нужно {}".format(pad, obj, facts[obj], val))
        return False

    # Шаг 2. Защита от зацикливания
    if goal in stack:
        log("{}  - зацикливание, цель уже проверяется".format(pad))
        return False
    stack.append(goal)

    # Шаг 3. Ищем правила, у которых ТО = наша цель, и доказываем их условия
    #        (каждое условие - это новая цель, поэтому вызываем prove сами у себя)
    candidates = [r for r in rules if r.conclusion == goal]
    for rule in candidates:
        log("{}  Пробуем правило: {}".format(pad, rule.text))
        all_ok = True
        for cond in rule.conditions:
            if not prove(cond, rules, facts, log, ask_func, stack, depth + 1):
                all_ok = False
                break  # одно условие не доказали - правило не подходит
        if all_ok:
            facts[obj] = val  # доказанная цель становится фактом
            log("{}  + цель доказана, в базу добавлен факт {} = {}".format(pad, obj, val))
            stack.pop()
            return True
        log("{}  правило не подошло".format(pad))
    stack.pop()

    # Шаг 4. Если объект не выводится НИ ОДНИМ правилом - это исходные данные,
    #        их можно только спросить у пользователя
    if not any(r.conclusion[0] == obj for r in rules):
        answer = ask_func(obj)
        if answer:
            facts[obj] = answer
            log("{}  Пользователь сообщил: {} = {}".format(pad, obj, answer))
            return answer == val
        log("{}  - сведений об объекте «{}» нет".format(pad, obj))
    return False


# ---------- 3. ИНТЕРФЕЙС ----------
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Экспертная система подбора выпечки (обратная цепочка)")
        self.root.geometry("980x600")

        self.rules = load_rules(RULES_FILE)
        self.facts = {}
        self.selected_index = None

        left_frame = tk.Frame(root, padx=8, pady=8)
        left_frame.pack(side="left", fill="both", expand=True)
        right_frame = tk.Frame(root, padx=8, pady=8)
        right_frame.pack(side="right", fill="both", expand=True)

        self._build_left(left_frame)
        self._build_right(right_frame)
        self._refresh_rules_list()

    # ----- левая половина: факты, цель, результат -----
    def _build_left(self, frame):
        tk.Label(frame, text="Начальное состояние (объект=значение)").pack(anchor="w")
        self.facts_input = tk.Text(frame, height=5)
        self.facts_input.pack(fill="x")
        self.facts_input.insert("1.0", "тесто=дрожжевое\nначинка=нет")

        tk.Label(frame, text="Целевая ситуация (объект=значение)").pack(anchor="w", pady=(8, 0))
        self.goal_input = tk.Entry(frame)
        self.goal_input.pack(fill="x")
        self.goal_input.insert(0, "изделие=ржаной_хлеб")

        tk.Button(frame, text="Доказать цель", bg="#A24CAF", fg="white",
                  command=self.do_prove).pack(fill="x", pady=8)

        tk.Label(frame, text="Рабочая база данных (после вывода):").pack(anchor="w")
        self.facts_view = tk.Listbox(frame, height=5)
        self.facts_view.pack(fill="x", pady=(0, 8))

        tk.Label(frame, text="Ход доказательства и результат:").pack(anchor="w")
        self.output = tk.Text(frame, height=15, state="disabled", bg="#f5f5f5")
        self.output.pack(fill="both", expand=True)

    def do_prove(self):
        # 1) читаем начальное состояние из поля ввода
        self.facts = {}
        for line in self.facts_input.get("1.0", "end").splitlines():
            if "=" in line:
                obj, val = pair(line)
                self.facts[obj] = val

        # 2) читаем цель
        goal_text = self.goal_input.get().strip()
        if "=" not in goal_text:
            messagebox.showerror("Ошибка", "Цель задаётся в виде объект=значение")
            return
        goal = pair(goal_text)

        # 3) функция-вопрос пользователю; повторно про отказ не спрашиваем
        refused = set()

        def ask_func(object_name):
            if object_name in refused:
                return ""
            answer = simpledialog.askstring(
                "Не хватает сведений",
                "Введите значение для объекта «{}»\n"
                "(оставьте пустым, если сведений нет):".format(object_name))
            answer = answer.strip() if answer else ""
            if not answer:
                refused.add(object_name)
            return answer

        # 4) запускаем доказательство и показываем итог
        self._clear_output()
        result = prove(goal, self.rules, self.facts, self._log, ask_func, [])
        self._log("")
        if result:
            self._log("ИТОГ: цель {} = {} ДОСТИЖИМА.".format(*goal))
        else:
            self._log("ИТОГ: цель {} = {} НЕ достижима.".format(*goal))
        self._refresh_facts_view()

    def _refresh_facts_view(self):
        self.facts_view.delete(0, "end")
        for obj, val in self.facts.items():
            self.facts_view.insert("end", "{} = {}".format(obj, val))

    def _clear_output(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

    def _log(self, message):
        self.output.configure(state="normal")
        self.output.insert("end", message + "\n")
        self.output.configure(state="disabled")
        self.output.see("end")

    def _build_right(self, frame):
        tk.Label(frame, text="База правил:").pack(anchor="w")
        self.rules_list = tk.Listbox(frame, height=16)
        self.rules_list.pack(fill="both", expand=True)
        self.rules_list.bind("<<ListboxSelect>>", self._on_rule_select)

        tk.Label(frame, text="Правило:").pack(anchor="w", pady=(8, 0))
        self.rule_edit = tk.Text(frame, height=3)
        self.rule_edit.pack(fill="x")

        btns = tk.Frame(frame)
        btns.pack(fill="x", pady=6)
        tk.Button(btns, text="Добавить", command=self.add_rule).pack(side="left", expand=True, fill="x")
        tk.Button(btns, text="Изменить выбранное", command=self.update_rule).pack(side="left", expand=True, fill="x")
        tk.Button(btns, text="Удалить выбранное", command=self.delete_rule).pack(side="left", expand=True, fill="x")

        tk.Button(frame, text="Обновить базу правил", bg="#2196F3", fg="white",
                  command=self.save_rules_to_file).pack(fill="x", pady=(6, 0))

    def _refresh_rules_list(self):
        self.rules_list.delete(0, "end")
        for i, rule in enumerate(self.rules, start=1):
            self.rules_list.insert("end", "{}. {}".format(i, rule.text))

    def _on_rule_select(self, event):
        selection = self.rules_list.curselection()
        if not selection:
            return
        self.selected_index = selection[0]
        self.rule_edit.delete("1.0", "end")
        self.rule_edit.insert("1.0", self.rules[self.selected_index].text)

    def _read_rule_from_editor(self):
        rule = line_in_rule(self.rule_edit.get("1.0", "end"))
        if rule is None:
            messagebox.showerror("Ошибка", "Правило не распознано.\nФормат: ЕСЛИ A=1 И B=2 ТО C=3")
        return rule

    def add_rule(self):
        rule = self._read_rule_from_editor()
        if rule:
            self.rules.append(rule)
            self._refresh_rules_list()

    def update_rule(self):
        if self.selected_index is None:
            messagebox.showinfo("Нет выбора", "Сначала выберите правило в списке.")
            return
        rule = self._read_rule_from_editor()
        if rule:
            self.rules[self.selected_index] = rule
            self._refresh_rules_list()

    def delete_rule(self):
        if self.selected_index is None:
            messagebox.showinfo("Нет выбора", "Сначала выберите правило в списке.")
            return
        del self.rules[self.selected_index]
        self.selected_index = None
        self.rule_edit.delete("1.0", "end")
        self._refresh_rules_list()

    def save_rules_to_file(self):
        save_rules(RULES_FILE, self.rules)
        messagebox.showinfo("Сохранено", "База правил сохранена в файл")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
