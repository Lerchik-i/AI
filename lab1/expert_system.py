import os
import tkinter as tk
from tkinter import messagebox, simpledialog

RULES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules.txt")
class Rule:
    def __init__(self, conditions, conclusion, text):
        self.conditions = conditions #условия
        self.conclusion = conclusion #то
        self.text = text #исходный текст
        self.used = False #использовалось ли

def line_in_rule(line):
    line = line.strip()
    if not line:
        return None
    if "ЕСЛИ" not in line or "ТО" not in line:
        return None

    after_if = line.split("ЕСЛИ", 1)[1]
    cond_part, concl_part = after_if.rsplit("ТО", 1)

    conditions = []
    for piece in cond_part.split(" И "):
        piece = piece.strip()
        if not piece:
            continue
        obj, val = piece.split("=", 1)
        conditions.append((obj.strip(), val.strip()))

    obj, val = concl_part.strip().split("=", 1)
    conclusion = (obj.strip(), val.strip())

    return Rule(conditions, conclusion, line)

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

def run_inference(rules, facts, log, ask_func):
    #log      — функция, для вывода в окно трассировки
    #ask_func — функция, которая спрашивает пользователя значение объекта
    while True:
        fired = False
        for rule in rules:
            if rule.used:
                continue
            conditions_ok = True
            for obj, val in rule.conditions:
                fact_value = facts.get(obj)
                if fact_value != val:
                    conditions_ok = False
                    break
            if conditions_ok:
                obj, val = rule.conclusion
                if facts.get(obj) != val:
                    facts[obj] = val
                    rule.used = True
                    log("Сработало правило: {}".format(rule.text))
                    log("   => в базу добавлен факт: {} = {}".format(obj, val))
                    fired = True
                    break
        if fired:
            continue 


        missing_object = None
        for rule in rules:
            if rule.used:
                continue
            contradiction = False
            missing_here = None
            for obj, val in rule.conditions:
                if obj in facts:
                    if facts[obj] != val:
                        contradiction = True
                        break
                elif missing_here is None:
                    missing_here = obj
            if not contradiction and missing_here is not None:
                missing_object = missing_here
                break

        if missing_object is None:
            log("Ни одно правило больше не может сработать. Вывод завершён.")
            return facts

        answer = ask_func(missing_object)
        if answer:
            facts[missing_object] = answer
            log("Пользователь добавил: {} = {}".format(missing_object, answer))
        else:
            log("Сведений об объекте «{}» нет. Вывод остановлен.".format(missing_object))
            return facts

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Экспертная система подбора выпечки")
        self.root.geometry("980x600")

        self.rules = load_rules('rules.txt')
        self.facts = {}

        # окно поделили
        left_frame = tk.Frame(root, padx=8, pady=8)
        left_frame.pack(side="left", fill="both", expand=True)

        right_frame = tk.Frame(root, padx=8, pady=8)
        right_frame.pack(side="right", fill="both", expand=True)

        self._build_left(left_frame)
        self._build_right(right_frame)
        self._refresh_rules_list()

    def _build_left(self, frame):
        tk.Label(frame, text="Начальное состояние", justify="left").pack(anchor="w")

        self.facts_input = tk.Text(frame, height=6)
        self.facts_input.pack(fill="x")
        self.facts_input.insert("1.0", "тесто=дрожжевое\nначинка=мясо")

        tk.Button(frame, text="Загрузить начальное состояние",
                  command=self.load_initial_state).pack(fill="x", pady=(4, 8))

        tk.Label(frame, text="Рабочая база данных:").pack(anchor="w")
        self.facts_view = tk.Listbox(frame, height=8)
        self.facts_view.pack(fill="x", pady=(0, 8))

        tk.Button(frame, text="Сделать вывод", bg="#A24CAF", fg="white",
                  command=self.do_inference).pack(fill="x", pady=(0, 8))

        tk.Label(frame, text="Результат:").pack(anchor="w")
        self.output = tk.Text(frame, height=15, state="disabled", bg="#f5f5f5")
        self.output.pack(fill="both", expand=True)

    def load_initial_state(self):
        """Читает текст из поля ввода и превращает его в словарь фактов."""
        self.facts = {}
        for rule in self.rules:
            rule.used = False  # сбрасываем флаги — начинаем вывод заново

        text = self.facts_input.get("1.0", "end").strip()
        for line in text.splitlines():
            line = line.strip()
            if not line or "=" not in line:
                continue
            obj, val = line.split("=", 1)
            self.facts[obj.strip()] = val.strip()

        self._refresh_facts_view()
        self._clear_output()
        self._log("Начальное состояние загружено.")

    def do_inference(self):
        if not self.facts:
            messagebox.showinfo("Нет данных", "Сначала загрузите начальное состояние.")
            return

        def ask_func(object_name):
            answer = simpledialog.askstring(
                "Не хватает сведений",
                "Ни одно правило не может сработать.\n"
                "Введите значение для объекта «{}»\n"
                "(оставьте пустым, если сведений нет):".format(object_name)
            )
            return answer.strip() if answer else ""

        run_inference(self.rules, self.facts, self._log, ask_func)
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

        self.selected_index = None

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

    def add_rule(self):
        text = self.rule_edit.get("1.0", "end").strip()
        rule = line_in_rule(text)
        if rule is None:
            messagebox.showerror("Ошибка", "Правило не распознано.\nПроверьте формат:\n"
                                            "ЕСЛИ A=1 И B=2 ТО C=3")
            return
        self.rules.append(rule)
        self._refresh_rules_list()

    def update_rule(self):
        if self.selected_index is None:
            messagebox.showinfo("Нет выбора", "Сначала выберите правило в списке.")
            return
        text = self.rule_edit.get("1.0", "end").strip()
        rule = line_in_rule(text)
        if rule is None:
            messagebox.showerror("Ошибка", "Правило не распознано.\nПроверьте формат:\n"
                                            "ЕСЛИ A=1 И B=2 ТО C=3")
            return
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
        save_rules('rules.txt', self.rules)
        messagebox.showinfo("Сохранено", "База правил сохранена в файл")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
