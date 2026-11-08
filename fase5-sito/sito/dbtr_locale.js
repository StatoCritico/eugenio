"use strict";
// Edifici di un DB topografico letto nel browser (pagina «Aggiungi edifici (DB topografico)», 07/11/2026), passati a
// Modelli 3D senza server: IndexedDB del sito (i GeoJSON di un comune superano i 5 MB della memoria della scheda), più un
// segnale nella memoria della scheda (sessionStorage) perché Modelli 3D li usi solo nella sessione aperta dalla pagina.
// Restano nel browser finché l'utente non li toglie o carica un altro file. Ogni accesso è protetto: in una finestra
// privata, o con i dati del sito bloccati, la pagina funziona lo stesso (senza passaggio a Modelli 3D).
(function () {
  const DB = "eugenio", NEGOZIO = "dbtr", CHIAVE = "locale", SEGNALE = "eugenio-dbtr-locale";
  function apri() {
    return new Promise((ok, no) => {
      let r;
      try { r = indexedDB.open(DB, 1); } catch (e) { no(e); return; }
      r.onupgradeneeded = () => { try { r.result.createObjectStore(NEGOZIO); } catch (e) { /* già c'è */ } };
      r.onsuccess = () => ok(r.result);
      r.onerror = () => no(r.error || new Error("IndexedDB non disponibile"));
    });
  }
  async function operazione(modo, fn) {
    const db = await apri();
    try {
      return await new Promise((ok, no) => {
        const t = db.transaction(NEGOZIO, modo), s = t.objectStore(NEGOZIO);
        const r = fn(s);
        t.oncomplete = () => ok(r && "result" in r ? r.result : undefined);
        t.onerror = () => no(t.error || new Error("IndexedDB: operazione non riuscita"));
        t.onabort = () => no(t.error || new Error("IndexedDB: spazio esaurito o accesso negato"));
      });
    } finally { db.close(); }
  }
  async function salva(dati) { await operazione("readwrite", (s) => s.put(dati, CHIAVE)); attiva(); }
  async function leggi() { try { return (await operazione("readonly", (s) => s.get(CHIAVE))) || null; } catch { return null; } }
  async function togli() {
    try { sessionStorage.removeItem(SEGNALE); } catch { /* niente */ }
    try { await operazione("readwrite", (s) => s.delete(CHIAVE)); } catch { /* niente */ }
  }
  function attiva() { try { sessionStorage.setItem(SEGNALE, "1"); } catch { /* niente */ } }
  function attivo() { try { return sessionStorage.getItem(SEGNALE) === "1"; } catch { return false; } }
  window.EUGENIO_DBTR_LOCALE = { salva, leggi, togli, attiva, attivo };
})();
