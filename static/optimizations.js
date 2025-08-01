// Enhanced frontend performance optimizations
// Request batching, virtual scrolling, and state management

class RequestBatcher {
    constructor(batchSize = 5, batchDelay = 100) {
        this.queue = [];
        this.processing = false;
        this.batchSize = batchSize;
        this.batchDelay = batchDelay;
        this.metrics = {
            totalRequests: 0,
            batchedRequests: 0,
            averageBatchSize: 0
        };
    }

    async addRequest(request) {
        this.queue.push(request);
        this.metrics.totalRequests++;
        
        if (!this.processing) {
            this.processing = true;
            setTimeout(() => this.processBatch(), this.batchDelay);
        }
    }

    async processBatch() {
        if (this.queue.length === 0) {
            this.processing = false;
            return;
        }

        const batch = this.queue.splice(0, this.batchSize);
        this.metrics.batchedRequests += batch.length;
        this.metrics.averageBatchSize = this.metrics.batchedRequests / (this.metrics.batchedRequests / batch.length);

        try {
            await Promise.all(batch.map(req => req()));
        } catch (error) {
            console.error('Batch processing error:', error);
        }

        if (this.queue.length > 0) {
            setTimeout(() => this.processBatch(), this.batchDelay);
        } else {
            this.processing = false;
        }
    }

    getMetrics() {
        return { ...this.metrics };
    }

    clear() {
        this.queue = [];
        this.processing = false;
    }
}

class VirtualChatScroller {
    constructor(container, itemHeight = 100, bufferSize = 5) {
        this.container = container;
        this.itemHeight = itemHeight;
        this.bufferSize = bufferSize;
        this.visibleItems = Math.ceil(window.innerHeight / itemHeight) + (bufferSize * 2);
        this.scrollTop = 0;
        this.renderWindow = { start: 0, end: this.visibleItems };
        this.items = [];
        this.renderedElements = new Map();
        
        this.setupScrollListener();
    }

    setupScrollListener() {
        this.container.addEventListener('scroll', 
            this.debounce(() => this.updateRenderWindow(), 16)
        );
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    setItems(items) {
        this.items = items;
        this.updateTotalHeight();
        this.updateRenderWindow();
    }

    updateTotalHeight() {
        const totalHeight = this.items.length * this.itemHeight;
        this.container.style.height = `${totalHeight}px`;
    }

    updateRenderWindow() {
        const scrollTop = this.container.scrollTop;
        const containerHeight = this.container.clientHeight;
        
        const start = Math.max(0, Math.floor(scrollTop / this.itemHeight) - this.bufferSize);
        const end = Math.min(
            this.items.length,
            Math.ceil((scrollTop + containerHeight) / this.itemHeight) + this.bufferSize
        );

        if (start !== this.renderWindow.start || end !== this.renderWindow.end) {
            this.renderWindow = { start, end };
            this.render();
        }
    }

    render() {
        const visibleItems = this.items.slice(this.renderWindow.start, this.renderWindow.end);
        const fragment = document.createDocumentFragment();

        // Remove elements outside render window
        for (const [index, element] of this.renderedElements) {
            if (index < this.renderWindow.start || index >= this.renderWindow.end) {
                element.remove();
                this.renderedElements.delete(index);
            }
        }

        // Create new elements for visible items
        visibleItems.forEach((item, relativeIndex) => {
            const actualIndex = this.renderWindow.start + relativeIndex;
            
            if (!this.renderedElements.has(actualIndex)) {
                const element = this.createItemElement(item, actualIndex);
                this.renderedElements.set(actualIndex, element);
                fragment.appendChild(element);
            }
        });

        this.container.appendChild(fragment);
    }

    createItemElement(item, index) {
        const element = document.createElement('div');
        element.className = 'chat-message';
        element.style.position = 'absolute';
        element.style.top = `${index * this.itemHeight}px`;
        element.style.height = `${this.itemHeight}px`;
        element.innerHTML = this.renderItemContent(item);
        return element;
    }

    renderItemContent(item) {
        return `
            <div class="message-content">
                <div class="message-header">
                    <span class="sender">${item.sender || 'User'}</span>
                    <span class="timestamp">${item.timestamp || new Date().toLocaleTimeString()}</span>
                </div>
                <div class="message-body">${item.content || item.message || ''}</div>
            </div>
        `;
    }

    scrollToBottom() {
        this.container.scrollTop = this.container.scrollHeight;
    }

    addItem(item) {
        this.items.push(item);
        this.updateTotalHeight();
        this.updateRenderWindow();
        
        // Auto-scroll to bottom if user is near bottom
        const isNearBottom = this.container.scrollTop + this.container.clientHeight >= 
                            this.container.scrollHeight - 100;
        
        if (isNearBottom) {
            this.scrollToBottom();
        }
    }
}

class StateManager {
    constructor() {
        this.state = {
            chatHistory: [],
            currentProvider: 'openai',
            currentModel: 'gpt-4o-mini',
            currentPersona: 'assistant',
            isProcessing: false,
            uploadedFiles: [],
            websocketConnected: false,
            typingUsers: new Set(),
            lastMessage: null
        };
        this.listeners = new Map();
        this.middleware = [];
    }

    // Subscribe to state changes
    subscribe(key, callback) {
        if (!this.listeners.has(key)) {
            this.listeners.set(key, new Set());
        }
        this.listeners.get(key).add(callback);

        // Return unsubscribe function
        return () => {
            const callbacks = this.listeners.get(key);
            if (callbacks) {
                callbacks.delete(callback);
            }
        };
    }

    // Add middleware for state changes
    addMiddleware(middleware) {
        this.middleware.push(middleware);
    }

    // Update state with middleware support
    async setState(updates) {
        const oldState = { ...this.state };
        const newState = { ...this.state, ...updates };

        // Run middleware
        for (const middleware of this.middleware) {
            const result = await middleware(oldState, newState, updates);
            if (result === false) {
                console.warn('State update blocked by middleware');
                return;
            }
        }

        // Apply updates
        this.state = newState;

        // Notify listeners
        for (const [key, value] of Object.entries(updates)) {
            const callbacks = this.listeners.get(key);
            if (callbacks) {
                callbacks.forEach(callback => {
                    try {
                        callback(value, oldState[key]);
                    } catch (error) {
                        console.error('State listener error:', error);
                    }
                });
            }
        }

        // Notify global listeners
        const globalCallbacks = this.listeners.get('*');
        if (globalCallbacks) {
            globalCallbacks.forEach(callback => {
                try {
                    callback(newState, oldState);
                } catch (error) {
                    console.error('Global state listener error:', error);
                }
            });
        }
    }

    getState(key = null) {
        return key ? this.state[key] : { ...this.state };
    }

    // Convenience methods
    addChatMessage(message) {
        const chatHistory = [...this.state.chatHistory, message];
        this.setState({ chatHistory, lastMessage: message });
    }

    setProcessing(isProcessing) {
        this.setState({ isProcessing });
    }

    setProvider(provider) {
        this.setState({ currentProvider: provider });
    }

    setModel(model) {
        this.setState({ currentModel: model });
    }

    addTypingUser(userId) {
        const typingUsers = new Set(this.state.typingUsers);
        typingUsers.add(userId);
        this.setState({ typingUsers });
    }

    removeTypingUser(userId) {
        const typingUsers = new Set(this.state.typingUsers);
        typingUsers.delete(userId);
        this.setState({ typingUsers });
    }
}

class PerformanceMonitor {
    constructor() {
        this.metrics = {
            requestTimes: [],
            renderTimes: [],
            memoryUsage: [],
            errors: []
        };
        this.startTime = performance.now();
    }

    startTimer(label) {
        return {
            label,
            startTime: performance.now(),
            end: () => {
                const duration = performance.now() - this.startTime;
                this.recordMetric(label, duration);
                return duration;
            }
        };
    }

    recordMetric(type, value) {
        if (!this.metrics[type]) {
            this.metrics[type] = [];
        }
        
        this.metrics[type].push({
            value,
            timestamp: Date.now()
        });

        // Keep only last 100 measurements
        if (this.metrics[type].length > 100) {
            this.metrics[type].shift();
        }
    }

    recordError(error, context) {
        this.metrics.errors.push({
            error: error.message,
            stack: error.stack,
            context,
            timestamp: Date.now()
        });
    }

    getAverageTime(type) {
        const times = this.metrics[type] || [];
        if (times.length === 0) return 0;
        
        const sum = times.reduce((acc, item) => acc + item.value, 0);
        return sum / times.length;
    }

    getMetrics() {
        return {
            averageRequestTime: this.getAverageTime('requestTimes'),
            averageRenderTime: this.getAverageTime('renderTimes'),
            totalErrors: this.metrics.errors.length,
            uptime: performance.now() - this.startTime,
            memoryUsage: performance.memory ? {
                used: performance.memory.usedJSHeapSize,
                total: performance.memory.totalJSHeapSize,
                limit: performance.memory.jsHeapSizeLimit
            } : null
        };
    }

    startPerformanceTracking() {
        // Track render performance
        if ('PerformanceObserver' in window) {
            const observer = new PerformanceObserver((list) => {
                list.getEntries().forEach((entry) => {
                    if (entry.entryType === 'measure') {
                        this.recordMetric('renderTimes', entry.duration);
                    }
                });
            });
            observer.observe({ entryTypes: ['measure'] });
        }

        // Track memory usage periodically
        setInterval(() => {
            if (performance.memory) {
                this.recordMetric('memoryUsage', performance.memory.usedJSHeapSize);
            }
        }, 30000); // Every 30 seconds
    }
}

class WebSocketManager {
    constructor(url) {
        this.url = url;
        this.socket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.messageQueue = [];
        this.eventListeners = new Map();
    }

    connect(userId, chatRoom = 'default') {
        if (this.isConnected) return;

        try {
            this.socket = new WebSocket(`${this.url}?user_id=${userId}&room=${chatRoom}`);
            
            this.socket.onopen = () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                
                // Send queued messages
                while (this.messageQueue.length > 0) {
                    const message = this.messageQueue.shift();
                    this.socket.send(JSON.stringify(message));
                }
                
                this.emit('connected');
            };

            this.socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.emit(data.type, data);
                } catch (error) {
                    console.error('WebSocket message parse error:', error);
                }
            };

            this.socket.onclose = () => {
                console.log('WebSocket disconnected');
                this.isConnected = false;
                this.emit('disconnected');
                this.attemptReconnect(userId, chatRoom);
            };

            this.socket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.emit('error', error);
            };

        } catch (error) {
            console.error('WebSocket connection failed:', error);
            this.attemptReconnect(userId, chatRoom);
        }
    }

    attemptReconnect(userId, chatRoom) {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.emit('reconnectFailed');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);
        
        setTimeout(() => {
            this.connect(userId, chatRoom);
        }, delay);
    }

    send(message) {
        if (this.isConnected && this.socket) {
            this.socket.send(JSON.stringify(message));
        } else {
            this.messageQueue.push(message);
        }
    }

    on(event, callback) {
        if (!this.eventListeners.has(event)) {
            this.eventListeners.set(event, new Set());
        }
        this.eventListeners.get(event).add(callback);
    }

    off(event, callback) {
        const listeners = this.eventListeners.get(event);
        if (listeners) {
            listeners.delete(callback);
        }
    }

    emit(event, data = null) {
        const listeners = this.eventListeners.get(event);
        if (listeners) {
            listeners.forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error('WebSocket event listener error:', error);
                }
            });
        }
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
        this.isConnected = false;
    }

    sendTypingStart() {
        this.send({ type: 'typing_start' });
    }

    sendTypingStop() {
        this.send({ type: 'typing_stop' });
    }

    sendChatMessage(message, messageId = null) {
        this.send({
            type: 'chat_message',
            message,
            message_id: messageId || Date.now().toString()
        });
    }
}

// Global instances
const requestBatcher = new RequestBatcher();
const stateManager = new StateManager();
const performanceMonitor = new PerformanceMonitor();

// Initialize performance tracking
performanceMonitor.startPerformanceTracking();

// Export for use in main application
window.TQChat = {
    RequestBatcher,
    VirtualChatScroller,
    StateManager,
    PerformanceMonitor,
    WebSocketManager,
    requestBatcher,
    stateManager,
    performanceMonitor
};
