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
});
