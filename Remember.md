# DB Budget - Edit Equipment (Mass & Power & Maturity) ADD ROW
Nel Db in tabella budget, all'inserimento da frontend per l'edit degli equipment lo script non risce a trovare e modificare i vecchi valori quindi ne crea di nuovi creando un nuovo id e row ad ogni modifica

# Product Tree - Tabella Budget Equipment
Visualizzazione corretta dei valori di massa, potenza e misurazione con risposta alla richiesta di edit, ma necessità di refresh della pagina a causa del db.

#       Product Tree:
        Latenza di creazione, modifica e cancellazione nodi, la comnunicazione con db è corretta ma vengono creati i nodi con qualche scondo di latenza quando richiesto, lato db e scripts py corretti, problema con prestazioni db (test fatti con ruolo admin)

# Role Permission
Attualemnte sonno stae implementate grandi modifiche alla role permission seguendo le linee guida nella sezione Team & Role, l'admin è sempre a pieni poteri non è stato modificato, mentre gli altri ruoli come User etc.. non possono invitare membri o creare pezzi sul product tree (*da rivedere*) o modificare ruoli.
- Il fattore da vedere oltre alle limitazioni imposte ai ruoli che sono assolutamente da visionare nel dettaglio, vanno anche corretti i frammenti di codice che consentono all'admin di modificare i ruoli degli utenti, dato che da front end può farlo ma ciò non va a cambiarsi da db

# COOKIE - Connector Google, Microsoft, SSO, etc..
Aggiunta neccessaria di coockie per il login con successivo adempimento dei login con connector e build project in google cloud

# SEND INVITATION MAIL
Rivedere la send verification mail, la function è creata, i codici di invito funzionano correttamente, le mail sono da rivedere dato che la api non è configurata correttamente nel portale SupaBase, il name deve essere RESEND_API_KEY