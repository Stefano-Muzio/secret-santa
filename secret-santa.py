
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import random
import secrets
import json
import base64
import hashlib
import html
import webbrowser

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class SecretSantaApp:

    def __init__(self, root):
        self.root = root
        self.root.title("🎅 Secret Santa")
        self.root.geometry("760x760")
        self.participants = []
        self.exclusions = []

        self.create_ui()

    def create_ui(self):
        # Partecipanti
        people = ttk.LabelFrame(self.root, text="Partecipanti")
        people.pack(fill="x", padx=10, pady=8)

        self.name_entry = ttk.Entry(people)
        self.name_entry.pack(side="left", fill="x", expand=True,
                             padx=5, pady=5)
        self.name_entry.bind("<Return>", lambda e: self.add_person())

        ttk.Button(people, text="Aggiungi",
                   command=self.add_person).pack(side="left", padx=5)

        self.people_list = tk.Listbox(people, height=7)
        self.people_list.pack(fill="x", padx=5, pady=5)

        ttk.Button(people, text="Rimuovi selezionato",
                   command=self.remove_person).pack(pady=5)

        # Esclusioni
        rules = ttk.LabelFrame(self.root, text="Coppie da evitare")
        rules.pack(fill="x", padx=10, pady=8)

        ttk.Label(rules, text="Chi NON regala a:").grid(
            row=0, column=0, padx=5, pady=5
        )

        self.giver = ttk.Combobox(rules, state="readonly", width=18)
        self.giver.grid(row=0, column=1, padx=5)

        self.receiver = ttk.Combobox(rules, state="readonly", width=18)
        self.receiver.grid(row=0, column=2, padx=5)

        ttk.Button(rules, text="Aggiungi",
                   command=self.add_exclusion).grid(
                       row=0, column=3, padx=5
                   )

        self.rules_list = tk.Listbox(rules, height=5)
        self.rules_list.grid(row=1, column=0, columnspan=4,
                             sticky="ew", padx=5, pady=5)

        ttk.Button(rules, text="Rimuovi esclusione",
                   command=self.remove_exclusion).grid(
                       row=2, column=0, columnspan=4, pady=5
                   )

        # GitHub Pages
        hosting = ttk.LabelFrame(
            self.root, text="Configurazione GitHub Pages"
        )
        hosting.pack(fill="x", padx=10, pady=8)

        ttk.Label(hosting, text="Indirizzo del sito:").pack(
            anchor="w", padx=5, pady=3
        )

        self.url_entry = ttk.Entry(hosting)
        self.url_entry.pack(fill="x", padx=5, pady=5)
        self.url_entry.insert(
            0, "https://TUONOME.github.io/secret-santa/"
        )

        # Sorteggio
        ttk.Button(
            self.root,
            text="🎅 ESEGUI SORTEGGIO E GENERA LINK",
            command=self.draw
        ).pack(fill="x", padx=10, pady=12)

        # Output
        output_frame = ttk.LabelFrame(
            self.root, text="Link da condividere"
        )
        output_frame.pack(fill="both", expand=True, padx=10, pady=8)

        self.output = tk.Text(output_frame, height=12, wrap="word")
        self.output.pack(fill="both", expand=True, padx=5, pady=5)

        ttk.Button(
            output_frame,
            text="Copia tutti i messaggi",
            command=self.copy_output
        ).pack(pady=5)

    # PARTECIPANTI

    def add_person(self):
        name = self.name_entry.get().strip()

        if not name:
            return

        if any(p.lower() == name.lower()
               for p in self.participants):
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

        self.exclusions = [
            (a, b) for a, b in self.exclusions
            if a != name and b != name
        ]

        self.refresh()

    # ESCLUSIONI

    def add_exclusion(self):
        giver = self.giver.get()
        receiver = self.receiver.get()

        if not giver or not receiver:
            return

        if giver == receiver:
            messagebox.showwarning(
                "Attenzione", "Non puoi escludere una persona da sé stessa."
            )
            return

        if (giver, receiver) not in self.exclusions:
            self.exclusions.append((giver, receiver))

        self.refresh()

    def remove_exclusion(self):
        selection = self.rules_list.curselection()
        if selection:
            self.exclusions.pop(selection[0])
            self.refresh()

    def refresh(self):
        self.people_list.delete(0, tk.END)

        for p in self.participants:
            self.people_list.insert(tk.END, p)

        self.giver["values"] = self.participants
        self.receiver["values"] = self.participants

        self.rules_list.delete(0, tk.END)

        for a, b in self.exclusions:
            self.rules_list.insert(tk.END, f"{a} → {b}")

    # SORTEGGIO

    def generate_draw(self):
        people = self.participants[:]
        forbidden = set(self.exclusions)
        forbidden.update((p, p) for p in people)

        givers = people[:]
        random.shuffle(givers)

        assignments = {}

        def solve(index, available):
            if index == len(givers):
                return True

            giver = givers[index]

            candidates = [
                p for p in available
                if (giver, p) not in forbidden
            ]

            random.shuffle(candidates)

            for receiver in candidates:
                assignments[giver] = receiver

                remaining = [
                    p for p in available if p != receiver
                ]

                if solve(index + 1, remaining):
                    return True

                del assignments[giver]

            return False

        if solve(0, people[:]):
            return assignments

        return None

    # CIFRATURA

    @staticmethod
    def encode(data):
        return base64.b64encode(data).decode("ascii")

    def encrypt_assignment(self, receiver):
        # Token casuale da 256 bit
        token = secrets.token_urlsafe(32)

        # La chiave deriva dal token, che non viene pubblicato
        # nella pagina HTML né nel percorso richiesto al server.
        raw_token = base64.urlsafe_b64decode(
            token + "=" * (-len(token) % 4)
        )

        key = hashlib.sha256(raw_token).digest()

        aes = AESGCM(key)
        nonce = secrets.token_bytes(12)

        ciphertext = aes.encrypt(
            nonce,
            receiver.encode("utf-8"),
            None
        )

        return token, {
            "nonce": self.encode(nonce),
            "ciphertext": self.encode(ciphertext)
        }

    # GENERAZIONE SITO

    def create_html(self):
        return r"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Secret Santa 🎅</title>
<style>
body {
    font-family: Arial, sans-serif;
    background: #f3f4f6;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    margin: 0;
    padding: 20px;
    box-sizing: border-box;
}
.card {
    background: white;
    max-width: 440px;
    width: 100%;
    padding: 35px 25px;
    border-radius: 20px;
    text-align: center;
    box-shadow: 0 5px 25px #0002;
}
h1 { color: #b22222; }
button {
    background: #b22222;
    color: white;
    border: 0;
    padding: 13px 25px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 16px;
}
.result {
    font-size: 30px;
    font-weight: bold;
    color: #228b22;
    margin: 25px 0;
    overflow-wrap: anywhere;
}
#error { color: #b22222; }
</style>
</head>
<body>
<div class="card">
    <h1>🎅 Secret Santa 🎄</h1>
    <p>Il tuo regalo di Natale va a...</p>
    <button id="reveal">SCOPRI IL DESTINATARIO</button>
    <div class="result" id="result"></div>
    <p id="error"></p>
    <p>🤫 Mi raccomando, non svelare il segreto!</p>
</div>

<script>
const button = document.getElementById("reveal");

function fromBase64(s) {
    const binary = atob(s);
    return Uint8Array.from(binary, c => c.charCodeAt(0));
}

button.addEventListener("click", async () => {
    button.disabled = true;

    try {
        const token = location.hash.substring(1);

        if (!token) {
            throw new Error("Link non valido.");
        }

        const normalized = token.replace(/-/g, "+")
                                 .replace(/_/g, "/");
        const rawToken = fromBase64(
            normalized + "=".repeat((4 - normalized.length % 4) % 4)
        );

        const digest = await crypto.subtle.digest(
            "SHA-256", rawToken
        );

        const key = await crypto.subtle.importKey(
            "raw", digest, "AES-GCM", false, ["decrypt"]
        );

        const response = await fetch("./data.json", {
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error("Impossibile recuperare il sorteggio.");
        }

        const data = await response.json();
        const record = data.records[token];

        if (!record) {
            throw new Error("Link non trovato.");
        }

        const plaintext = await crypto.subtle.decrypt(
            {
                name: "AES-GCM",
                iv: fromBase64(record.nonce)
            },
            key,
            fromBase64(record.ciphertext)
        );

        const decoder = new TextDecoder();
        const receiver = decoder.decode(plaintext);

        document.getElementById("result").textContent = receiver;
        button.textContent = "DESTINATARIO SCOPERTO 🎁";

    } catch (error) {
        document.getElementById("error").textContent =
            "Non riesco a mostrare il risultato. Controlla il link.";
        button.disabled = false;
    }
});
</script>
</body>
</html>
"""

    def draw(self):
        if len(self.participants) < 2:
            messagebox.showwarning(
                "Attenzione", "Servono almeno due partecipanti."
            )
            return

        base_url = self.url_entry.get().strip()

        if not base_url.startswith("https://"):
            messagebox.showwarning(
                "Indirizzo non valido",
                "Inserisci l'indirizzo HTTPS del tuo sito GitHub Pages."
            )
            return

        if "TUONOME" in base_url or not base_url.endswith("/"):
            messagebox.showwarning(
                "Indirizzo da completare",
                "Inserisci il tuo vero indirizzo GitHub Pages, "
                "terminando con /"
            )
            return

        assignments = self.generate_draw()

        if assignments is None:
            messagebox.showerror(
                "Sorteggio impossibile",
                "Non esiste un sorteggio che rispetti tutte le esclusioni."
            )
            return

        # Cartella di pubblicazione
        output_dir = Path.cwd() / "SecretSanta_output"
        output_dir.mkdir(exist_ok=True)

        records = {}
        links = {}

        for giver, receiver in assignments.items():
            token, encrypted = self.encrypt_assignment(receiver)

            records[token] = encrypted
            links[giver] = base_url + "#" + token

        # Archivio cifrato
        data = {"records": records}

        (output_dir / "data.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        # Pagina web
        (output_dir / "index.html").write_text(
            self.create_html(),
            encoding="utf-8"
        )

        # Messaggi
        messages = []

        for giver in self.participants:
            messages.append(
                f"Ciao {giver}! 🎅\n"
                f"Il tuo Secret Santa è pronto!\n"
                f"Apri questo link per scoprire chi devi regalare:\n"
                f"{links[giver]}\n"
            )

        messages_text = "\n--------------------\n\n".join(messages)

        (output_dir / "messaggi.txt").write_text(
            messages_text,
            encoding="utf-8"
        )

        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, messages_text)

        messagebox.showinfo(
            "Sorteggio completato!",
            "Estrazione completata!\n\n"
            "File generati in:\n"
            f"{output_dir}\n\n"
            "Ora devi caricare index.html e data.json "
            "nel repository GitHub."
        )

    def copy_output(self):
        text = self.output.get("1.0", tk.END).strip()

        if not text:
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(text)

        messagebox.showinfo("Copiato", "Messaggi copiati!")


if __name__ == "__main__":
    root = tk.Tk()
    app = SecretSantaApp(root)
    root.mainloop()
