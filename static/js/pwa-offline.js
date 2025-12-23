// PWA Offline functionality with local storage
class OfflineManager {
    constructor() {
        this.dbName = 'ExpiryTrackerDB';
        this.dbVersion = 1;
        this.itemsStore = 'items';
        this.initDB();
        this.setupEventListeners();
    }

    initDB() {
        const request = indexedDB.open(this.dbName, this.dbVersion);

        request.onerror = () => {
            console.error('IndexedDB error:', request.error);
        };

        request.onsuccess = () => {
            this.db = request.result;
            console.log('IndexedDB initialized');
        };

        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains(this.itemsStore)) {
                const store = db.createObjectStore(this.itemsStore, { keyPath: 'id', autoIncrement: true });
                store.createIndex('name', 'name', { unique: false });
                store.createIndex('expiry_date', 'expiry_date', { unique: false });
            }
        };
    }

    setupEventListeners() {
        // Listen for online/offline events
        window.addEventListener('online', () => {
            this.syncData();
            this.showNotification('Back online! Syncing data...', 'success');
        });

        window.addEventListener('offline', () => {
            this.showNotification('You are offline. Changes will be saved locally.', 'warning');
        });

        // Intercept form submissions for offline support
        document.addEventListener('submit', (e) => {
            if (!navigator.onLine && e.target.id === 'add-item-form') {
                e.preventDefault();
                this.saveItemOffline(e.target);
            }
        });
    }

    async saveItemOffline(form) {
        const formData = new FormData(form);
        const item = {
            name: formData.get('name'),
            category: formData.get('category'),
            expiry_date: formData.get('expiry_date'),
            quantity: formData.get('quantity'),
            notes: formData.get('notes'),
            barcode: formData.get('barcode'),
            created_at: new Date().toISOString(),
            synced: false
        };

        try {
            const transaction = this.db.transaction([this.itemsStore], 'readwrite');
            const store = transaction.objectStore(this.itemsStore);
            const request = store.add(item);

            request.onsuccess = () => {
                this.showNotification('Item saved offline! Will sync when online.', 'success');
                form.reset();
                this.displayOfflineItems();
            };

            request.onerror = () => {
                this.showNotification('Error saving item offline.', 'error');
            };
        } catch (error) {
            console.error('Error saving item offline:', error);
        }
    }

    async syncData() {
        if (!this.db) return;

        try {
            const transaction = this.db.transaction([this.itemsStore], 'readonly');
            const store = transaction.objectStore(this.itemsStore);
            const request = store.getAll();

            request.onsuccess = () => {
                const unsyncedItems = request.result.filter(item => !item.synced);
                if (unsyncedItems.length > 0) {
                    this.syncItemsToServer(unsyncedItems);
                }
            };
        } catch (error) {
            console.error('Error syncing data:', error);
        }
    }

    async syncItemsToServer(items) {
        for (const item of items) {
            try {
                const response = await fetch('/api/items/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken()
                    },
                    body: JSON.stringify(item)
                });

                if (response.ok) {
                    // Mark as synced
                    const transaction = this.db.transaction([this.itemsStore], 'readwrite');
                    const store = transaction.objectStore(this.itemsStore);
                    item.synced = true;
                    store.put(item);
                }
            } catch (error) {
                console.error('Error syncing item:', error);
            }
        }
    }

    displayOfflineItems() {
        if (!this.db) return;

        const transaction = this.db.transaction([this.itemsStore], 'readonly');
        const store = transaction.objectStore(this.itemsStore);
        const request = store.getAll();

        request.onsuccess = () => {
            const items = request.result;
            const offlineItemsContainer = document.getElementById('offline-items');
            if (offlineItemsContainer) {
                offlineItemsContainer.innerHTML = '';

                if (items.length > 0) {
                    offlineItemsContainer.innerHTML = '<h4>Offline Items (Not Synced)</h4>';
                    items.forEach(item => {
                        const itemDiv = document.createElement('div');
                        itemDiv.className = 'card mb-2';
                        itemDiv.innerHTML = `
                            <div class="card-body">
                                <h5 class="card-title">${item.name}</h5>
                                <p class="card-text">Expires: ${item.expiry_date}</p>
                                <small class="text-muted">Category: ${item.category}</small>
                            </div>
                        `;
                        offlineItemsContainer.appendChild(itemDiv);
                    });
                }
            }
        };
    }

    getCSRFToken() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        return csrfToken ? csrfToken.value : '';
    }

    showNotification(message, type = 'info') {
        // Simple notification system
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

// Initialize offline manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if ('indexedDB' in window) {
        window.offlineManager = new OfflineManager();
    } else {
        console.warn('IndexedDB not supported. Offline functionality disabled.');
    }
});
