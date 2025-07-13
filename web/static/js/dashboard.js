// Dashboard JavaScript for real-time updates and interactivity

class CatanDashboard {
    constructor() {
        this.socket = null;
        this.ratingChart = null;
        this.activeGames = new Map();
        this.init();
    }

    init() {
        this.connectSocket();
        this.loadInitialData();
        this.setupEventListeners();
        this.initChart();
    }

    connectSocket() {
        this.socket = io();

        this.socket.on('connect', () => {
            console.log('Connected to server');
            this.updateConnectionStatus(true);
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.updateConnectionStatus(false);
        });

        this.socket.on('game_update', (data) => {
            this.handleGameUpdate(data);
        });

        this.socket.on('leaderboard_update', (data) => {
            this.updateLeaderboard(data.leaderboard);
        });
    }

    updateConnectionStatus(connected) {
        const indicator = document.getElementById('connection-status');
        const text = document.getElementById('connection-text');
        
        if (connected) {
            indicator.classList.add('connected');
            text.textContent = 'Connected';
        } else {
            indicator.classList.remove('connected');
            text.textContent = 'Disconnected';
        }
    }

    async loadInitialData() {
        try {
            // Load leaderboard
            const leaderboardResponse = await fetch('/api/leaderboard');
            const leaderboardData = await leaderboardResponse.json();
            this.updateLeaderboard(leaderboardData.leaderboard);
            this.updateTotalGames(leaderboardData.total_games);
            
            // Load recent games
            const gamesResponse = await fetch('/api/games');
            const gamesData = await gamesResponse.json();
            this.updateRecentGames(gamesData);
            
            // Load active games
            const activeGamesResponse = await fetch('/api/active-games');
            const activeGamesData = await activeGamesResponse.json();
            this.updateActiveGames(activeGamesData);
            
        } catch (error) {
            console.error('Error loading initial data:', error);
        }
    }

    updateLeaderboard(leaderboard) {
        const tbody = document.getElementById('leaderboard-body');
        tbody.innerHTML = '';
        
        const chartData = {
            labels: [],
            ratings: []
        };
        
        leaderboard.forEach((entry, index) => {
            const row = document.createElement('tr');
            const modelName = entry.model.split('/').pop();
            const winRate = entry.stats.win_rate || 0;
            
            row.innerHTML = `
                <td>${entry.rank}</td>
                <td>${modelName}</td>
                <td>${Math.round(entry.rating)}</td>
                <td>${entry.stats.games_played || 0}</td>
                <td>${(winRate * 100).toFixed(1)}%</td>
            `;
            
            tbody.appendChild(row);
            
            // Collect data for chart
            chartData.labels.push(modelName);
            chartData.ratings.push(entry.rating);
        });
        
        // Update chart
        this.updateChart(chartData);
        
        // Update last updated time
        document.getElementById('last-updated').textContent = 
            new Date().toLocaleTimeString();
    }

    updateRecentGames(games) {
        const container = document.getElementById('recent-games-list');
        container.innerHTML = '';
        
        games.slice(0, 10).forEach(game => {
            const gameItem = document.createElement('div');
            gameItem.className = 'recent-game-item';
            if (game.winner) {
                const winnerColor = Object.entries(game.players)
                    .find(([color, model]) => model === game.winner)?.[0];
                if (winnerColor) {
                    gameItem.classList.add(`winner-${winnerColor.toLowerCase()}`);
                }
            }
            
            const timestamp = new Date(game.start_time).toLocaleString();
            const players = `${game.players.RED.split('/').pop()} vs ${game.players.BLUE.split('/').pop()}`;
            
            gameItem.innerHTML = `
                <div class="game-info">
                    <div>
                        <strong>${players}</strong>
                        <div class="game-timestamp">${timestamp}</div>
                    </div>
                    <div>
                        <span>Winner: ${game.winner ? game.winner.split('/').pop() : 'N/A'}</span>
                        <span> (${game.total_turns || 0} turns)</span>
                    </div>
                </div>
            `;
            
            gameItem.addEventListener('click', () => this.showGameDetails(game.game_id));
            container.appendChild(gameItem);
        });
    }

    updateActiveGames(games) {
        const container = document.getElementById('active-games-list');
        container.innerHTML = '';
        
        this.activeGames.clear();
        games.forEach(game => {
            this.activeGames.set(game.game_id, game);
            
            const gameItem = document.createElement('div');
            gameItem.className = 'game-item';
            gameItem.id = `active-game-${game.game_id}`;
            
            const players = `${game.players.RED.split('/').pop()} vs ${game.players.BLUE.split('/').pop()}`;
            
            gameItem.innerHTML = `
                <div class="game-players">${players}</div>
                <div class="game-turn">Turn ${game.current_turn}</div>
                <div class="game-status"></div>
            `;
            
            container.appendChild(gameItem);
        });
        
        document.getElementById('active-game-count').textContent = games.length;
    }

    handleGameUpdate(update) {
        console.log('Game update:', update);
        
        switch (update.type) {
            case 'game_start':
                this.addActiveGame(update.game_id, update.data);
                break;
            case 'action':
                this.updateGameProgress(update.game_id, update.data);
                break;
            case 'game_end':
                this.removeActiveGame(update.game_id);
                this.loadInitialData(); // Reload all data
                break;
        }
    }

    addActiveGame(gameId, data) {
        const game = {
            game_id: gameId,
            players: data.players,
            current_turn: 0,
            started: new Date().toISOString()
        };
        
        this.activeGames.set(gameId, game);
        this.updateActiveGames(Array.from(this.activeGames.values()));
    }

    updateGameProgress(gameId, data) {
        const game = this.activeGames.get(gameId);
        if (game) {
            game.current_turn = data.turn;
            const gameElement = document.getElementById(`active-game-${gameId}`);
            if (gameElement) {
                gameElement.querySelector('.game-turn').textContent = `Turn ${data.turn}`;
            }
        }
    }

    removeActiveGame(gameId) {
        this.activeGames.delete(gameId);
        this.updateActiveGames(Array.from(this.activeGames.values()));
    }

    updateTotalGames(count) {
        document.getElementById('total-games').textContent = count;
    }

    async showGameDetails(gameId) {
        try {
            const response = await fetch(`/api/game/${gameId}`);
            const game = await response.json();
            
            const modal = document.getElementById('game-modal');
            const details = document.getElementById('game-details');
            
            const players = Object.entries(game.players)
                .map(([color, model]) => `${color}: ${model.split('/').pop()}`)
                .join('<br>');
            
            const duration = game.end_time && game.start_time
                ? this.calculateDuration(game.start_time, game.end_time)
                : 'N/A';
            
            details.innerHTML = `
                <h3>Game ${gameId}</h3>
                <p><strong>Players:</strong><br>${players}</p>
                <p><strong>Winner:</strong> ${game.winner_model || 'N/A'}</p>
                <p><strong>Total Turns:</strong> ${game.total_turns || 0}</p>
                <p><strong>Duration:</strong> ${duration}</p>
                <p><strong>Start Time:</strong> ${new Date(game.start_time).toLocaleString()}</p>
                ${game.error ? `<p><strong>Error:</strong> ${game.error}</p>` : ''}
                
                <h4>Actions Summary</h4>
                <div style="max-height: 300px; overflow-y: auto;">
                    ${this.formatActions(game.actions || [])}
                </div>
            `;
            
            modal.style.display = 'block';
        } catch (error) {
            console.error('Error loading game details:', error);
        }
    }

    formatActions(actions) {
        if (actions.length === 0) return '<p>No actions recorded</p>';
        
        const summary = actions.slice(-10).map(action => `
            <div style="margin-bottom: 8px; padding: 8px; background: rgba(255,255,255,0.05); border-radius: 4px;">
                <strong>Turn ${action.turn}</strong> - ${action.player}: ${action.action}
            </div>
        `).join('');
        
        return summary;
    }

    calculateDuration(start, end) {
        const startTime = new Date(start);
        const endTime = new Date(end);
        const durationMs = endTime - startTime;
        
        const minutes = Math.floor(durationMs / 60000);
        const seconds = Math.floor((durationMs % 60000) / 1000);
        
        return `${minutes}m ${seconds}s`;
    }

    initChart() {
        const ctx = document.getElementById('rating-chart').getContext('2d');
        this.ratingChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Elo Rating',
                    data: [],
                    backgroundColor: 'rgba(52, 152, 219, 0.6)',
                    borderColor: 'rgba(52, 152, 219, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        min: 1200,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#ecf0f1'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#ecf0f1'
                        }
                    }
                }
            }
        });
    }

    updateChart(data) {
        if (this.ratingChart) {
            this.ratingChart.data.labels = data.labels;
            this.ratingChart.data.datasets[0].data = data.ratings;
            this.ratingChart.update();
        }
    }

    setupEventListeners() {
        // Modal close button
        document.querySelector('.close').addEventListener('click', () => {
            document.getElementById('game-modal').style.display = 'none';
        });
        
        // Click outside modal to close
        window.addEventListener('click', (event) => {
            const modal = document.getElementById('game-modal');
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
        
        // Refresh data every 30 seconds
        setInterval(() => {
            this.loadInitialData();
        }, 30000);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new CatanDashboard();
});