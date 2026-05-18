const OFFLINE_CORE_ASSETS = [
  '/capture/',
  '/manifest.json',
  '/static/receipts/capture.js',
  '/static/receipts/capture.css',
  '/static/vendor/alpinejs/cdn.min.js',
  '/static/pwa/icon.svg',
];

document.addEventListener('alpine:init', () => {
  Alpine.data('receiptCapture', () => ({
    db: null,
    online: navigator.onLine,
    offlineReadyState: 'checking',
    previewUrl: '',
    queuedCount: 0,
    status: 'Ready to capture a receipt.',
    syncing: false,
    uploadProgress: 0,
    activeUploadName: '',
    processingUpload: false,

    async init() {
      this.db = await this.openDb();
      await this.refreshQueue();
      this.monitorOfflineReady();
      await this.refreshOfflineReady();
      window.addEventListener('online', async () => {
        this.online = true;
        await this.refreshOfflineReady();
        await this.syncQueue();
      });
      window.addEventListener('offline', () => {
        this.online = false;
        this.status = 'Offline. New captures will stay on this device.';
      });
      if (this.online) await this.syncQueue();
    },

    monitorOfflineReady() {
      if (!('serviceWorker' in navigator)) {
        this.offlineReadyState = 'unavailable';
        return;
      }
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        void this.refreshOfflineReady();
      });
      window.setTimeout(() => {
        void this.refreshOfflineReady();
      }, 1500);
    },

    async refreshOfflineReady() {
      if (!globalThis.isSecureContext || !('serviceWorker' in navigator) || !('caches' in window)) {
        this.offlineReadyState = 'unavailable';
        return;
      }
      try {
        await navigator.serviceWorker.ready;
        const matches = await Promise.all(OFFLINE_CORE_ASSETS.map((path) => caches.match(path)));
        this.offlineReadyState = matches.every(Boolean) ? 'ready' : 'checking';
      } catch (error) {
        this.offlineReadyState = 'checking';
      }
    },

    offlineReadyText() {
      if (this.offlineReadyState === 'ready') return 'Offline ready';
      if (this.offlineReadyState === 'unavailable') return 'Offline mode unavailable';
      return 'Preparing offline mode...';
    },

    openDb() {
      return new Promise((resolve, reject) => {
        const request = indexedDB.open('salt-helper-receipts', 1);
        request.onupgradeneeded = () => {
          const db = request.result;
          if (!db.objectStoreNames.contains('queue')) {
            db.createObjectStore('queue', { keyPath: 'hash' });
          }
        };
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
    },

    tx(mode) {
      return this.db.transaction('queue', mode).objectStore('queue');
    },

    requestToPromise(request) {
      return new Promise((resolve, reject) => {
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
    },

    getCookie(name) {
      const cookies = document.cookie ? document.cookie.split('; ') : [];
      for (const cookie of cookies) {
        const [key, ...valueParts] = cookie.split('=');
        if (key === name) return decodeURIComponent(valueParts.join('='));
      }
      return '';
    },

    csrfToken() {
      return this.getCookie('csrftoken');
    },

    async handleFile(event) {
      const file = event.target.files[0];
      if (!file) return;
      if (this.previewUrl) URL.revokeObjectURL(this.previewUrl);
      this.previewUrl = URL.createObjectURL(file);
      const queueId = this.queueId();
      await this.saveRecord({
        hash: queueId,
        file,
        name: file.name || `${queueId}.jpg`,
        type: file.type || 'image/jpeg',
        size: file.size,
        createdAt: new Date().toISOString(),
      });
      event.target.value = '';
      await this.refreshQueue();
      this.status = 'Saved locally. Sync will run while this screen is open.';
      if (this.online) await this.syncQueue();
    },

    queueId() {
      if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
      return `queued-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    },

    async saveRecord(record) {
      await this.requestToPromise(this.tx('readwrite').put(record));
    },

    async records() {
      return this.requestToPromise(this.tx('readonly').getAll());
    },

    async removeRecord(hash) {
      await this.requestToPromise(this.tx('readwrite').delete(hash));
    },

    async refreshQueue() {
      const records = await this.records();
      this.queuedCount = records.length;
    },

    resetUploadState() {
      this.uploadProgress = 0;
      this.activeUploadName = '';
      this.processingUpload = false;
    },

    startUpload(record) {
      this.activeUploadName = record.name || 'receipt';
      this.uploadProgress = 0;
      this.processingUpload = false;
      this.status = `Uploading ${this.activeUploadName}... 0%`;
    },

    uploadRecord(record) {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/receipts/upload');
        xhr.responseType = 'json';
        const csrfToken = this.csrfToken();
        if (csrfToken) xhr.setRequestHeader('X-CSRFToken', csrfToken);

        xhr.upload.onprogress = (event) => {
          if (!event.lengthComputable) {
            this.status = `Uploading ${this.activeUploadName}...`;
            return;
          }
          this.uploadProgress = Math.round((event.loaded / event.total) * 100);
          this.status = `Uploading ${this.activeUploadName}... ${this.uploadProgress}%`;
        };

        xhr.upload.onload = () => {
          this.uploadProgress = 100;
          this.processingUpload = true;
          this.status = `Upload complete. Reading receipt details for ${this.activeUploadName} on the server...`;
        };

        xhr.onload = () => {
          this.processingUpload = false;
          resolve({ status: xhr.status, body: xhr.response });
        };

        xhr.onerror = () => {
          this.processingUpload = false;
          reject(new Error('Upload failed'));
        };

        xhr.onabort = () => {
          this.processingUpload = false;
          reject(new Error('Upload aborted'));
        };

        const form = new FormData();
        form.append('image', record.file, record.name);
        xhr.send(form);
      });
    },

    async syncQueue() {
      if (!this.online || this.syncing || !this.db) return;
      const records = await this.records();
      if (!records.length) {
        this.queuedCount = 0;
        this.resetUploadState();
        this.status = 'No local receipts waiting to sync.';
        return;
      }
      this.syncing = true;
      try {
        for (const record of records) {
          this.startUpload(record);
          const response = await this.uploadRecord(record);
          if (response.status === 201 || response.status === 409) {
            await this.removeRecord(record.hash);
          } else if (response.status === 401 || response.status === 403) {
            this.resetUploadState();
            this.status = 'Sign in again to resume syncing queued receipts.';
            break;
          } else {
            this.resetUploadState();
            this.status = `Sync paused: server returned ${response.status}.`;
            break;
          }
        }
      } catch (error) {
        this.resetUploadState();
        this.status = 'Sync paused. Keep the app open and try again when online.';
      } finally {
        this.syncing = false;
        await this.refreshQueue();
        if (!this.queuedCount) {
          this.resetUploadState();
          this.status = 'All local receipts are synced.';
        }
      }
    },
  }));
});
