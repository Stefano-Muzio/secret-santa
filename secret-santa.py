import tkinter as tk
from tkinter import ttk, messagebox
import random
import secrets
import html
import os
from pathlib import Path


class SecretSantaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎅 Secret Santa")
        self.root.geometry("720x720")

        self.participants = []
        self.exclusions = []

        self.create_ui()

    def create_ui(self):
        # --- Partecipanti ---
        frame_people = ttk.LabelFrame(self.root, text="Partecipanti")
        frame_people.pack(fill="x", padx=10, pady=10)

        self.name_entry = ttk.Entry(frame_people)
        self.name_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        self.name_entry.bind("<Return>", lambda e: self.add_person())

        ttk.Button(
            frame_people, text="Aggiungi", command=self.add_person
        ).pack(side="left", padx=5)

        self.people_list = tk.Listbox(frame_people, height=8)
        self.people_list.pack(fill="x", padx=5, pady=5)

        ttk.Button(
            frame_people, text="Rimuovi selezionato",
            command=self.remove_person
        ).pack(pady=5)

        # --- Esclusioni ---
        frame_rules = ttk.LabelFrame(self.root, text="Coppie da evitare")
        frame_rules.pack(fill="x", padx=10, pady=10)

        ttk.Label(frame_rules, text="Chi NON regala a:").grid(
            row=0, column=0, padx=5, pady=5
        )

        self.giver = ttk.Combobox(frame_rules, state="readonly")
        self.giver.grid(row=0, column=1, padx=5, pady=5)

        self.receiver = ttk.Combobox(frame_rules, state="readonly")
        self.receiver.grid(row=0, column=2, padx=5, pady=5)

        ttk.Button(
            frame_rules, text="Aggiungi esclusione",
            command=self.add_exclusion
        ).grid(row=0, column=3, padx=5)

        self.rules_list = tk.Listbox(frame_rules, height=6)
        self.rules_list.grid(row=1, column=0, columnspan=4,
                            sticky="ew", padx=5, pady=5)

        ttk.Button(
            frame_rules, text="Rimuovi esclusione selezionata",
            command=self.remove_exclusion
        ).grid(row=2, column=0, columnspan=4, pady=5)

        # --- Sorteggio ---
        frame_draw = ttk.LabelFrame(self.root, text="Sorteggio")
        frame_draw.pack(fill="x", padx=10, pady=10)

        ttk.Button(
            frame_draw, text="🎅 Esegui sorteggio e genera pagine",
            command=self.draw
        ).pack(fill="x", padx=10, pady=10)

        # --- Messaggi ---
        frame_output = ttk.LabelFrame(
            self.root, text="Messaggi da condividere"
        )
        frame_output.pack(fill="both", expand=True, padx=10, pady=10)

        self.output = tk.Text(frame_output, height=12, wrap="word")
        self.output.pack(fill="both", expand=True, padx=5, pady=5)

        ttk.Button(
            frame_output, text="Copia tutto",
            command=self.copy_output
        ).pack(pady=5)

    # ---------------- PARTECIPANTI ----------------

    def add_person(self):
        name = self.name_entry.get().strip()

        if not name:
            return

        if any(p.lower() == name.lower() for p in self.participants):
            messagebox.showwarning("Attenzione", "Nome già presente.")
            return

        self.participants.append(name)
        self.name_entry.delete(0, tk.END)
        self.refresh()

    def remove_person(self):
        selection = self.people_list.curselection()

        if not selection:
            return

        name = self.people_list.get(selection[0])
        self.participants.remove(name)

        # Rimuove le regole che coinvolgono la persona eliminata
        self.exclusions = [
            (a, b) for a, b in self.exclusions
            if a != name and b != name
        ]

        self.refresh()

    # ---------------- ESCLUSIONI ----------------

    def add_exclusion(self):
        giver = self.giver.get()
        receiver = self.receiver.get()

        if not giver or not receiver:
            return

        if giver == receiver:
            messagebox.showwarning(
                "Attenzione",
                "Non puoi inserire la stessa persona in entrambi i campi."
            )
            return

        rule = (giver, receiver)

        if rule in self.exclusions:
            return

        self.exclusions.append(rule)
        self.refresh()

    def remove_exclusion(self):
        selection = self.rules_list.curselection()

        if not selection:
            return

        self.exclusions.pop(selection[0])
        self.refresh()

    def refresh(self):
        self.people_list.delete(0, tk.END)

        for person in self.participants:
            self.people_list.insert(tk.END, person)

        self.giver["values"] = self.participants
        self.receiver["values"] = self.participants

        self.rules_list.delete(0, tk.END)

        for a, b in self.exclusions:
            self.rules_list.insert(tk.END, f"{a}  →  {b}")

    # ---------------- ALGORITMO ----------------

    def generate_draw(self):
        people = self.participants[:]

        if len(people) < 2:
            raise ValueError("Servono almeno due partecipanti.")

        forbidden = set(self.exclusions)

        # Nessuno può regalare a sé stesso
        forbidden.update((p, p) for p in people)

        # Algoritmo di assegnazione casuale con backtracking
        givers = people[:]
        random.shuffle(givers)

        assignments = {}

        def solve(index, available):
            if index == len(givers):
                return True

            giver = givers[index]

            candidates = [
                r for r in available
                if (giver, r) not in forbidden
            ]

            random.shuffle(candidates)

            for receiver in candidates:
                assignments[giver] = receiver

                if solve(index + 1, [
                    p for p in available if p != receiver
                ]):
                    return True

                assignments.pop(giver, None)

            return False

        if solve(0, people[:]):
            return assignments

        return None

    # ---------------- GENERAZIONE HTML ----------------

    def draw(self):
        if len(self.participants) < 2:
            messagebox.showwarning(
                "Attenzione", "Inserisci almeno due partecipanti."
            )
            return

        try:
            assignments = self.generate_draw()
        except ValueError as e:
            messagebox.showwarning("Attenzione", str(e))
            return

        if assignments is None:
            messagebox.showerror(
                "Sorteggio impossibile",
                "Non esiste un sorteggio che rispetti tutte le regole.\n"
                "Prova a rimuovere qualche esclusione."
            )
            return

        # Cartella di output
        output_dir = Path.cwd() / "SecretSanta_output"
        output_dir.mkdir(exist_ok=True)

        # Genera una pagina individuale per ogni partecipante
        links = {}

        for giver, receiver in assignments.items():
            token = secrets.token_urlsafe(12)
            filename = f"{token}.html"
            filepath = output_dir / filename

            links[giver] = filepath

            safe_receiver = html.escape(receiver)

            page = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Secret Santa 🎅</title>
<style>
body {{
    font-family: Arial, sans-serif;
    text-align: center;
    padding: 50px 20px;
    background: #f5f5f5;
}}
.card {{
    background: white;
    max-width: 500px;
    margin: auto;
    padding: 40px 20px;
    border-radius: 20px;
    box-shadow: 0 4px 20px rgba(0,0,0,.1);
}}
h1 {{ color: #b22222; }}
.name {{ font-size: 2em; color: #228b22; }}
</style>
</head>
<body>
<div class="card">
<h1>🎅 Secret Santa 🎄</h1>
<p>Quest'anno tu farai un regalo a:</p>
<div class="name">{safe_receiver}</div>
<p>Mi raccomando... non svelare il segreto! 🤫</p>
</div>
</body>
</html>
"""

            filepath.write_text(page, encoding="utf-8")

        # Prepara messaggi
        self.output.delete("1.0", tk.END)

        for giver in self.participants:
            link = links[giver].as_uri()

            message = (
                f"Ciao {giver}! 🎅\n"
                f"Scopri chi devi regalare:\n{link}\n\n"
            )

            self.output.insert(tk.END, message)

        self.output.insert(
            tk.END,
            "\nPagine HTML generate nella cartella:\n"
            f"{output_dir}\n\n"
            "ATTENZIONE: questi sono link locali sul tuo computer.\n"
            "Per renderli accessibili agli amici via Internet, "
            "serve pubblicarli su un hosting."
        )

        messagebox.showinfo(
            "Sorteggio completato",
            "Sorteggio eseguito!\n\n"
            f"Le pagine sono state create in:\n{output_dir}"
        )

    # ---------------- COPIA ----------------

    def copy_output(self):
        text = self.output.get("1.0", tk.END).strip()

        if not text:
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(text)

        messagebox.showinfo(
            "Copiato", "Testo copiato negli appunti!"
        )


if __name__ == "__main__":
    root = tk.Tk()
    app = SecretSantaApp(root)
    root.mainloop()