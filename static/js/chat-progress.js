/**
 * Chat progress indicator for TQ GenAI Chat
 * Shows a progress bar during AI response generation
 */

class ChatProgress {
    constructor() {
        this.progressBar = null;
        this.createProgressBar();
    }

    createProgressBar() {
        // Create progress bar element if it doesn't exist
        if (!document.getElementById('chat-progress-bar')) {
            const progressBar = document.createElement('div');
            progressBar.id = 'chat-progress-bar';
            progressBar.className = 'chat-progress-bar';
            progressBar.innerHTML = `
                <div class="progress-track">
                    <div class="progress-fill"></div>
                </div>
                <div class="progress-status">
                    <span class="progress-message">Generating response</span>
                    <span class="typing-dots">
                        <span class="dot"></span>
                        <span class="dot"></span>
                        <span class="dot"></span>
                    </span>
                </div>
            `;
            document.body.appendChild(progressBar);
            this.progressBar = progressBar;

            // Add cancel button
            const cancelBtn = document.createElement('button');
            cancelBtn.className = 'progress-cancel';
            cancelBtn.innerHTML = '<i class="fas fa-times"></i>';
            cancelBtn.setAttribute('aria-label', 'Cancel response generation');
            progressBar.appendChild(cancelBtn);

            // Add click handler for cancel button
            cancelBtn.addEventListener('click', () => {
                this.cancelResponse();
            });
        }
    }

    start() {
        if (!this.progressBar) this.createProgressBar();

        // Reset and show progress bar
        const fill = this.progressBar.querySelector('.progress-fill');
        fill.style.width = '0%';
        this.progressBar.classList.add('active');

        // Animate to 90% quickly, then slow down
        setTimeout(() => {
            fill.style.width = '90%';
            fill.style.transition = 'width 15s cubic-bezier(0.1, 0.05, 0.1, 0.05)';
        }, 50);
    }

    updateStatus(message) {
        const statusEl = this.progressBar.querySelector('.progress-message');
        if (statusEl) {
            statusEl.textContent = message;
        }
    }

    complete() {
        if (!this.progressBar) return;

        // Finish animation
        const fill = this.progressBar.querySelector('.progress-fill');
        fill.style.transition = 'width 0.3s ease-out';
        fill.style.width = '100%';

        // Hide after completion
        setTimeout(() => {
            this.progressBar.classList.remove('active');
        }, 500);
    }

    setProgress(percent) {
        if (!this.progressBar) return;

        const fill = this.progressBar.querySelector('.progress-fill');
        fill.style.transition = 'width 0.3s ease';
        fill.style.width = `${percent}%`;
    }

    cancelResponse() {
        // Stop current response generation
        if (window.chatClient && typeof window.chatClient.cancelResponse === 'function') {
            window.chatClient.cancelResponse();
        }

        this.complete();
    }
}

// Initialize progress bar on page load
document.addEventListener('DOMContentLoaded', () => {
    window.chatProgress = new ChatProgress();

    // Add styles for progress bar
    const style = document.createElement('style');
    style.textContent = `
        .chat-progress-bar {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            width: 300px;
            background-color: var(--card-bg);
            border-radius: var(--border-radius-lg);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            padding: 12px 15px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            z-index: 1000;
            opacity: 0;
            transform: translateX(-50%) translateY(20px);
            transition: all 0.3s ease;
            pointer-events: none;
        }

        .chat-progress-bar.active {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
            pointer-events: all;
        }

        .progress-track {
            height: 6px;
            background-color: rgba(0, 0, 0, 0.1);
            border-radius: 3px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--primary-color), var(--accent-color));
            width: 0%;
            transition: width 0.3s ease-out;
        }

        .progress-status {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85em;
            color: var(--text-color);
        }

        .typing-dots {
            display: flex;
            gap: 4px;
        }

        .typing-dots .dot {
            width: 4px;
            height: 4px;
            background-color: var(--text-color);
            border-radius: 50%;
            opacity: 0.6;
        }

        .typing-dots .dot:nth-child(1) {
            animation: pulseDot 1.2s infinite 0s;
        }

        .typing-dots .dot:nth-child(2) {
            animation: pulseDot 1.2s infinite 0.4s;
        }

        .typing-dots .dot:nth-child(3) {
            animation: pulseDot 1.2s infinite 0.8s;
        }

        @keyframes pulseDot {
            0% { transform: scale(1); opacity: 0.6; }
            50% { transform: scale(1.5); opacity: 1; }
            100% { transform: scale(1); opacity: 0.6; }
        }

        .progress-cancel {
            position: absolute;
            top: -8px;
            right: -8px;
            width: 20px;
            height: 20px;
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            cursor: pointer;
            transition: all 0.2s ease;
            color: var(--text-color);
        }

        .progress-cancel:hover {
            background-color: var(--danger-color);
            color: white;
            border-color: var(--danger-color);
        }
    `;
    document.head.appendChild(style);
});
