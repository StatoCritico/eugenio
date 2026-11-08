"use strict";
// Web Worker delle ombre (fase 10): profilo d'orizzonte di ogni punto di campionamento delle aree FV e delle parti
// esposte delle facciate (72 direzioni, ostacoli entro 250 m), così l'ombra di ogni ora è solo una consultazione.
// Messaggio: { id, punti: [[x, y, z]], ostacoli: [{ ring, cima }], direzioni, lontano? } in metri locali; `lontano` è
// l'orizzonte del terreno (Copernicus DEM, dal server), unito con il massimo direzione per direzione (Fase B).
// Risposta: { id, orizzonti: [Array(72)] }.
importScripts("edifici_calcoli.js?v=20261107b");
self.onmessage = (e) => {
  const { id, punti, ostacoli, direzioni, lontano } = e.data;
  const E = self.EUGENIO_EDIFICI;
  const orizzonti = punti.map((p) => Array.from(E.uniscio(E.orizzonte(p, ostacoli, direzioni || 72, 250), lontano)));
  self.postMessage({ id, orizzonti });
};
