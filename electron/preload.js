"use strict";

const { contextBridge, ipcRenderer } = require("electron");

const BACKEND_URL = "http://127.0.0.1:8000";

contextBridge.exposeInMainWorld("electronAPI", {
  backendUrl: BACKEND_URL,

  // Recherche native dans la page (Ctrl+F dans le compte rendu ouvert).
  // findInPage est géré par le process main sur la webContents : ça marche
  // quel que soit le rendu (éditeur tiptap contenteditable OU markdown).
  find: {
    start: (text, options) => ipcRenderer.send("find:start", text, options),
    stop: () => ipcRenderer.send("find:stop"),
    onResult: (cb) => {
      const h = (_e, result) => cb(result);
      ipcRenderer.on("find:result", h);
      return () => ipcRenderer.removeListener("find:result", h);
    },
  },

  // Notifications natives 5 min avant chaque réunion d'agenda. Le main
  // process tire la notif et envoie via webContents.send l'ID de la
  // réunion à ouvrir. Renderer s'abonne via cette API et nettoie le
  // listener au démontage (la fonction retournée).
  notifications: {
    onOpenMeeting: (cb) => {
      const h = (_e, payload) => cb(payload);
      ipcRenderer.on("notification:open-meeting", h);
      return () => ipcRenderer.removeListener("notification:open-meeting", h);
    },
  },

  // System tray (mode arrière-plan).
  //   - onOpenJob : déclenché quand l'utilisateur clique sur un item tray
  //     qui doit ouvrir un job précis (post-stop d'un enregistrement,
  //     notif « CR prêt »).
  //   - onFirstHideHint : 1re fois que la fenêtre est cachée au tray,
  //     le main demande au renderer d'afficher une popup explicative.
  //   - notifySettingsChanged : à appeler après update des paramètres
  //     pour que main resynchronise son cache (quitOnClose,
  //     launchAtStartup → flag Windows Login Item).
  tray: {
    onOpenJob: (cb) => {
      const h = (_e, payload) => cb(payload);
      ipcRenderer.on("tray:open-job", h);
      return () => ipcRenderer.removeListener("tray:open-job", h);
    },
    onFirstHideHint: (cb) => {
      const h = () => cb();
      ipcRenderer.on("tray:first-hide-hint", h);
      return () => ipcRenderer.removeListener("tray:first-hide-hint", h);
    },
    notifySettingsChanged: () => ipcRenderer.send("settings:changed"),
  },

  // Popup riche du tray (Next.js route /tray-popup chargée dans une
  // BrowserWindow borderless). Les boutons du popup délèguent toutes les
  // actions au main process pour que celui-ci pilote uniformément :
  // notifications natives Windows, ouverture de la fenêtre principale,
  // gestion du flag liveReportReady, etc. (Sinon on devrait dupliquer
  // toute cette logique côté popup ET côté menu clic-droit.)
  trayWindow: {
    openMainApp: (payload) =>
      ipcRenderer.send("tray-popup:open-main-app", payload || {}),
    quitApp: () => ipcRenderer.send("tray-popup:quit-app"),
    startRecording: (opts) =>
      ipcRenderer.send("tray-popup:start-recording",
        typeof opts === "object" && opts !== null ? opts : { eventId: opts || null }),
    stopRecording: () => ipcRenderer.send("tray-popup:stop-recording"),
  },

  // Fenêtre flottante « Assistant live » : ouverture/fermeture à la demande.
  advisor: {
    open: () => ipcRenderer.send("advisor:open"),
    close: () => ipcRenderer.send("advisor:close"),
  },
});
