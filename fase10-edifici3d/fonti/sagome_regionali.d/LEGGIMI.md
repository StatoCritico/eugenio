# Sagome regionali delle altre regioni

Un file `.toml` per regione con uno o più blocchi `[[fonte]]` con gli stessi campi di `../sagome_regionali.toml`.
`edifici3d/sagome_regionali.carica()` li legge dopo il file principale, in ordine di nome.
