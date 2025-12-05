document.addEventListener('DOMContentLoaded', () => {
    const inputSection = document.getElementById('input-section');
    const progressSection = document.getElementById('progress-section');
    const resultSection = document.getElementById('result-section');
    const taskInput = document.getElementById('task-input');
    const sendBtn = document.getElementById('send-btn');
    const logOutput = document.getElementById('log-output');
    const downloadBtn = document.getElementById('download-btn');
    const restartBtn = document.getElementById('restart-btn');

    let currentRunId = null;
    let pollInterval = null;

    sendBtn.addEventListener('click', async () => {
        const task = taskInput.value.trim();
        if (!task) return;

        inputSection.classList.remove('active');
        setTimeout(() => {
            progressSection.classList.add('active');
        }, 500);

        try {
            const response = await fetch('/api/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ task })
            });
            const data = await response.json();
            currentRunId = data.run_id;
            startPolling();
        } catch (error) {
            console.error('Error starting task:', error);
            logOutput.textContent = "Error starting task: " + error;
        }
    });

    function startPolling() {
        if (pollInterval) clearInterval(pollInterval);
        pollInterval = setInterval(async () => {
            if (!currentRunId) return;

            try {
                const response = await fetch(`/api/status/${currentRunId}`);
                const data = await response.json();

                if (data.logs) {
                    logOutput.textContent = data.logs;
                    const logWindow = document.querySelector('.log-window');
                    logWindow.scrollTop = logWindow.scrollHeight;
                }

                if (data.status === 'completed') {
                    clearInterval(pollInterval);
                    showResult(data.run_id);
                } else if (data.status === 'failed') {
                    clearInterval(pollInterval);
                    logOutput.textContent += "\n\nTASK FAILED.";
                }
            } catch (error) {
                console.error('Polling error:', error);
            }
        }, 2000);
    }

    function showResult(runId) {
        progressSection.classList.remove('active');
        setTimeout(() => {
            resultSection.classList.add('active');
            document.getElementById('download-app-btn').href = `/api/download_app/${runId}`;
            document.getElementById('download-code-btn').href = `/api/download_code/${runId}`;
        }, 500);
    }

    restartBtn.addEventListener('click', () => {
        resultSection.classList.remove('active');
        taskInput.value = '';
        logOutput.textContent = '';
        setTimeout(() => {
            inputSection.classList.add('active');
        }, 500);
    });
});
