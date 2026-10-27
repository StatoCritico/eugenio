// Pagina Contattaci: compone l'email per eugenio@statocritico.it e la apre nel programma di posta di chi scrive.
// Niente viene inviato al server di EuGEnio.
(function () {
  "use strict";
  const DEST = "eugenio@statocritico.it";
  const f = document.getElementById("modulo-contatti");
  const esito = document.getElementById("c-esito");
  const val = (id) => document.getElementById(id).value.trim();

  function messaggio(testo, errore) {
    esito.textContent = testo;
    esito.classList.toggle("errore", !!errore);
  }

  function controlla() {
    for (const id of ["c-nome", "c-email", "c-oggetto", "c-testo"]) {
      const el = document.getElementById(id);
      if (!el.checkValidity()) {
        el.focus();
        const nome = document.querySelector(`label[for="${id}"]`).textContent.replace(/\(facoltativo\)/, "").trim();
        messaggio(`Manca o non è valido: ${nome}.`, true);
        return false;
      }
    }
    return true;
  }

  function componi() {
    const tipo = f.querySelector('input[name="tipo"]:checked').value;
    const oggetto = `[EuGEnio – ${tipo}] ${val("c-oggetto")}`;
    const righe = [
      val("c-testo"),
      "",
      "—",
      `Nome: ${val("c-nome")}`,
      `Email: ${val("c-email")}`,
    ];
    if (val("c-ente")) righe.push(`Ente o azienda: ${val("c-ente")}`);
    if (val("c-ruolo")) righe.push(`Ruolo: ${val("c-ruolo")}`);
    righe.push(`Tipo: ${tipo}`, "Inviato dalla pagina Contattaci di eugenio.statocritico.it");
    return { oggetto, corpo: righe.join("\n") };
  }

  f.addEventListener("submit", (e) => {
    e.preventDefault();
    if (!controlla()) return;
    const { oggetto, corpo } = componi();
    const url = `mailto:${DEST}?subject=${encodeURIComponent(oggetto)}&body=${encodeURIComponent(corpo)}`;
    messaggio("Si sta aprendo il tuo programma di posta: controlla il messaggio e premi Invia. " +
      "Se non si apre niente, usa “Copia il testo”.");
    window.location.href = url;
  });

  document.getElementById("c-copia").addEventListener("click", async () => {
    if (!controlla()) return;
    const { oggetto, corpo } = componi();
    const tutto = `A: ${DEST}\nOggetto: ${oggetto}\n\n${corpo}`;
    try {
      await navigator.clipboard.writeText(tutto);
      messaggio(`Testo copiato: incollalo in una nuova email a ${DEST}.`);
    } catch (err) {
      messaggio(`Non riesco a copiare in automatico: seleziona il testo del modulo e scrivi a ${DEST}.`, true);
    }
  });
})();
