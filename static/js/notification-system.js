/**
 * Modern notification system for TQ GenAI Chat
 * Provides toast notifications, alerts, and status messages
 */

class NotificationSystem {
    constructor() {
        this.container = null;
        this.createContainer();
        this.queue = [];
        this.maxVisible = 3;
        this.visibleCount = 0;
        this.sounds = {
            success: '/static/sounds/success.mp3',
            error: '/static/sounds/error.mp3',
            info: '/static/sounds/notification.mp3',
            warning: '/static/sounds/warning.mp3'
        };

        // Create audio elements for accessibility
        this.audioElements = {};
        Object.keys(this.sounds).forEach(type => {
            this.audioElements[type] = new Audio(this.sounds[type]);
            this.audioElements[type].volume = 0.5;
        });
    }

    createContainer() {
        if (this.container) return;

        this.container = document.createElement('div');
        this.container.className = 'notifications-container';
        document.body.appendChild(this.container);
    }

    notify({
        message,
        type = 'info',
        duration = 5000,
        dismissible = true,
        sound = true,
        icon = null
    }) {
        // Create the notification
        const notification = document.createElement('div');
        notification.className = `notification notification-${type} notification-enter`;
        notification.setAttribute('role', 'alert');
        notification.setAttribute('aria-live', 'polite');

        // Set default icons by type
        if (!icon) {
            switch (type) {
                case 'success': icon = 'check-circle'; break;
                case 'error': icon = 'times-circle'; break;
                case 'warning': icon = 'exclamation-triangle'; break;
                default: icon = 'info-circle';
            }
        }

        // Create notification content
        notification.innerHTML = `
            <div class="notification-icon">
                <i class="fas fa-${icon}"></i>
            </div>
            <div class="notification-content">
                <div class="notification-message">${message}</div>
                ${duration > 0 ? '<div class="notification-progress"></div>' : ''}
            </div>
            ${dismissible ? '<button class="notification-close" aria-label="Close notification">&times;</button>' : ''}
        `;

        // Handle dismissal
        if (dismissible) {
            const closeBtn = notification.querySelector('.notification-close');
            closeBtn.addEventListener('click', () => this.dismiss(notification));
        }

        // Add to queue or display immediately
        if (this.visibleCount >= this.maxVisible) {
            this.queue.push({ notification, duration });
        } else {
            this.show(notification, duration);
        }

        // Play sound if enabled
        if (sound && window.uiPreferences?.preferences?.sounds) {
            this.playSound(type);
        }

        return notification;
    }

    show(notification, duration) {
        // Add to container
        this.container.appendChild(notification);
        this.visibleCount++;

        // Trigger animation
        setTimeout(() => {
            notification.classList.remove('notification-enter');
            notification.classList.add('notification-show');
        }, 10);

        // Animate progress bar if duration is set
        if (duration > 0) {
            const progress = notification.querySelector('.notification-progress');
            if (progress) {
                progress.style.transition = `width ${duration}ms linear`;
                // Trigger animation in next frame
                requestAnimationFrame(() => {
                    progress.style.width = '0%';
                });
            }

            // Auto-dismiss after duration
            setTimeout(() => {
                this.dismiss(notification);
            }, duration);
        }
    }

    dismiss(notification) {
        // Don't dismiss if already dismissing
        if (notification.classList.contains('notification-exit')) return;

        // Animate out
        notification.classList.remove('notification-show');
        notification.classList.add('notification-exit');

        // Remove after animation
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);

                this.visibleCount--;

                // Show next notification from queue if any
                if (this.queue.length > 0) {
                    const next = this.queue.shift();
                    this.show(next.notification, next.duration);
                }
            }
        }, 300); // Match CSS transition duration
    }

    success(message, options = {}) {
        return this.notify({
            message,
            type: 'success',
            ...options
        });
    }

    error(message, options = {}) {
        return this.notify({
            message,
            type: 'error',
            ...options
        });
    }

    warning(message, options = {}) {
        return this.notify({
            message,
            type: 'warning',
            ...options
        });
    }

    info(message, options = {}) {
        return this.notify({
            message,
            type: 'info',
            ...options
        });
    }

    playSound(type) {
        if (this.audioElements[type]) {
            // Reset and play
            const audio = this.audioElements[type];
            audio.currentTime = 0;
            audio.play().catch(e => {
                console.warn('Failed to play notification sound:', e);
            });
        }
    }

    clearAll() {
        // Clear all visible notifications
        const notifications = this.container.querySelectorAll('.notification');
        notifications.forEach(notification => {
            this.dismiss(notification);
        });

        // Clear queue
        this.queue = [];
    }
}

// Initialize notification system on page load
document.addEventListener('DOMContentLoaded', () => {
    window.notifications = new NotificationSystem();

    // Add global functions for easy usage
    window.notify = (message, options) => window.notifications.notify({ message, ...options });
    window.toast = {
        success: (message, options) => window.notifications.success(message, options),
        error: (message, options) => window.notifications.error(message, options),
        warning: (message, options) => window.notifications.warning(message, options),
        info: (message, options) => window.notifications.info(message, options)
    };
});
