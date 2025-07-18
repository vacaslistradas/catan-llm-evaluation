// Minimal Catan Dashboard

class CatanDashboard {
    constructor() {
        this.socket = null;
        this.currentGameId = null;
        this.boardState = null;
        this.init();
    }

    init() {
        this.connectSocket();
        this.setupEventListeners();
        this.checkForActiveGame();
    }

    connectSocket() {
        this.socket = io();

        this.socket.on('connect', () => {
            console.log('Connected to server');
            this.updateConnectionStatus(true);
            // Request current game state on reconnection
            this.checkForActiveGame();
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.updateConnectionStatus(false);
        });

        this.socket.on('game_update', (data) => {
            console.log('Received game_update:', data);
            this.handleGameUpdate(data);
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

    handleGameUpdate(update) {
        console.log('Update type:', update.type);
        console.log('Update data:', update.data);
        
        switch (update.type) {
            case 'game_start':
                console.log('Game start - showing game');
                console.log('Players data:', update.data.players);
                this.showGame(update.game_id, update.data);
                // Update board if provided
                if (update.data.board) {
                    this.updateBoard(update.data.board);
                }
                break;
                
            case 'action':
                // If this is the first update, show the game
                if (!this.currentGameId) {
                    console.log('First action - showing game');
                    // Don't set default names - wait for proper game_start event
                    this.currentGameId = update.game_id;
                }
                this.updateGame(update.game_id, update.data);
                
                // Also update buildings and roads if present in game state
                if (update.data.game_state && update.data.game_state.board) {
                    const board = update.data.game_state.board;
                    if (board.buildings || board.roads) {
                        this.updateBuildings(board.buildings || []);
                        this.updateRoads(board.roads || []);
                    }
                }
                break;
                
            case 'game_end':
                this.endGame();
                break;
        }
    }

    checkForActiveGame() {
        // Check if there's an active game we should display
        fetch('/api/active-games')
            .then(response => response.json())
            .then(games => {
                if (games && games.length > 0) {
                    console.log('Found active game:', games[0]);
                    // There's an active game, request its current state
                    const activeGame = games[0];
                    if (activeGame.game_id && !this.currentGameId) {
                        // Simulate a game_start event to restore the UI
                        this.showGame(activeGame.game_id, {
                            players: activeGame.players
                        });
                    }
                }
            })
            .catch(err => console.error('Error checking for active games:', err));
    }

    showGame(gameId, gameData) {
        this.currentGameId = gameId;
        
        // Hide waiting state, show game state
        document.getElementById('waiting-state').style.display = 'none';
        document.getElementById('game-state').style.display = 'flex';
        
        // Set player names - show just the model name part
        if (gameData.players) {
            const redModel = gameData.players.RED || 'Red Player';
            const blueModel = gameData.players.BLUE || 'Blue Player';
            
            // Extract just the model name from provider/model format
            const redName = redModel.includes('/') ? redModel.split('/').pop() : redModel;
            const blueName = blueModel.includes('/') ? blueModel.split('/').pop() : blueModel;
            
            document.getElementById('red-player-name').textContent = redName;
            document.getElementById('blue-player-name').textContent = blueName;
        }
        
        // Initialize board display with empty board
        this.initializeBoard();
        
        // Clear action list
        document.getElementById('actions-list').innerHTML = '';
    }

    initializeBoard() {
        // Create a legal Catan board representation
        const boardDisplay = document.getElementById('board-display');
        boardDisplay.innerHTML = '';
        
        // Standard Catan board layout - 19 hexes total
        // Using Catanatron's coordinate system
        const hexPositions = [
            // Row 0 (top) - 3 hexes
            {coord: '(0, 0)', x: 2, y: 0},
            {coord: '(1, 0)', x: 3, y: 0},
            {coord: '(2, 0)', x: 4, y: 0},
            
            // Row 1 - 4 hexes (offset by 0.5 to the left)
            {coord: '(0, 1)', x: 1.5, y: 1},
            {coord: '(1, 1)', x: 2.5, y: 1},
            {coord: '(2, 1)', x: 3.5, y: 1},
            {coord: '(3, 1)', x: 4.5, y: 1},
            
            // Row 2 (middle) - 5 hexes
            {coord: '(0, 2)', x: 1, y: 2},
            {coord: '(1, 2)', x: 2, y: 2},
            {coord: '(2, 2)', x: 3, y: 2},
            {coord: '(3, 2)', x: 4, y: 2},
            {coord: '(4, 2)', x: 5, y: 2},
            
            // Row 3 - 4 hexes (offset by 0.5 to the left)
            {coord: '(0, 3)', x: 1.5, y: 3},
            {coord: '(1, 3)', x: 2.5, y: 3},
            {coord: '(2, 3)', x: 3.5, y: 3},
            {coord: '(3, 3)', x: 4.5, y: 3},
            
            // Row 4 (bottom) - 3 hexes
            {coord: '(0, 4)', x: 2, y: 4},
            {coord: '(1, 4)', x: 3, y: 4},
            {coord: '(2, 4)', x: 4, y: 4}
        ];
        
        // Default resource distribution for legal Catan board
        const defaultResources = [
            'wood', 'wood', 'wood', 'wood',
            'brick', 'brick', 'brick',
            'sheep', 'sheep', 'sheep', 'sheep',
            'wheat', 'wheat', 'wheat', 'wheat',
            'ore', 'ore', 'ore',
            'desert'
        ];
        
        // Default number distribution (no number on desert)
        const defaultNumbers = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12];
        
        // Store hex elements by coordinate for later updates
        this.hexElements = {};
        
        // Calculate hex dimensions and grid layout
        const hexWidth = 86;
        const hexHeight = 100;
        
        // Dynamically calculate center position based on container size
        const containerWidth = boardDisplay.clientWidth;
        const containerHeight = boardDisplay.clientHeight;
        
        // Center the grid so that hex (2,2) is at the center of the container
        // Hex (2,2) is at grid position x=3, y=2
        const centerHexX = 3;
        const centerHexY = 2;
        
        // Calculate where hex (2,2) should be positioned to be at container center
        const containerCenterX = containerWidth / 2;
        const containerCenterY = containerHeight / 2;
        
        // Calculate the offset needed to center hex (2,2)
        const boardOffsetX = containerCenterX - (centerHexX * hexWidth + hexWidth / 2);
        const boardOffsetY = containerCenterY - (centerHexY * hexHeight * 0.75 + hexHeight / 2);
        
        // Create hex elements
        hexPositions.forEach((pos, index) => {
            const hex = document.createElement('div');
            hex.className = 'hex-tile';
            hex.dataset.coord = pos.coord;
            
            // Use default resources for initial display
            const resource = defaultResources[index] || 'desert';
            hex.classList.add(`hex-${resource}`);
            
            // Position the hex using calculated offsets
            const x = boardOffsetX + pos.x * hexWidth;
            const y = boardOffsetY + pos.y * hexHeight * 0.75;
            hex.style.left = `${x}px`;
            hex.style.top = `${y}px`;
            
            // Add placeholder for number/robber
            const centerDiv = document.createElement('div');
            centerDiv.className = 'hex-center';
            hex.appendChild(centerDiv);
            
            boardDisplay.appendChild(hex);
            this.hexElements[pos.coord] = hex;
        });
        
        // Board will be updated with real data when we receive it
        this.boardState = null;
        
        // Calculate node positions for buildings immediately
        this.calculateNodePositions();
        console.log('Total node positions calculated:', Object.keys(this.nodePositions).length);
    }
    
    calculateNodePositions() {
        const hexWidth = 86;
        const hexHeight = 100;
        const vSpacing = hexHeight * 0.75;
        
        // Use the SAME dynamic centering logic as initializeBoard
        const boardDisplay = document.getElementById('board-display');
        const containerWidth = boardDisplay.clientWidth;
        const containerHeight = boardDisplay.clientHeight;
        
        // Use the same hex positions as initializeBoard
        const hexPositions = [
            {coord: '(0, 0)', x: 2, y: 0}, {coord: '(1, 0)', x: 3, y: 0}, {coord: '(2, 0)', x: 4, y: 0},
            {coord: '(0, 1)', x: 1.5, y: 1}, {coord: '(1, 1)', x: 2.5, y: 1}, {coord: '(2, 1)', x: 3.5, y: 1}, {coord: '(3, 1)', x: 4.5, y: 1},
            {coord: '(0, 2)', x: 1, y: 2}, {coord: '(1, 2)', x: 2, y: 2}, {coord: '(2, 2)', x: 3, y: 2}, {coord: '(3, 2)', x: 4, y: 2}, {coord: '(4, 2)', x: 5, y: 2},
            {coord: '(0, 3)', x: 1.5, y: 3}, {coord: '(1, 3)', x: 2.5, y: 3}, {coord: '(2, 3)', x: 3.5, y: 3}, {coord: '(3, 3)', x: 4.5, y: 3},
            {coord: '(0, 4)', x: 2, y: 4}, {coord: '(1, 4)', x: 3, y: 4}, {coord: '(2, 4)', x: 4, y: 4}
        ];
        
        // Center the grid so that hex (2,2) is at the center of the container (same as initializeBoard)
        // Hex (2,2) is at grid position x=3, y=2
        const centerHexX = 3;
        const centerHexY = 2;
        
        // Calculate where hex (2,2) should be positioned to be at container center
        const containerCenterX = containerWidth / 2;
        const containerCenterY = containerHeight / 2;
        
        // Calculate the offset needed to center hex (2,2)
        const boardOffsetX = containerCenterX - (centerHexX * hexWidth + hexWidth / 2);
        const boardOffsetY = containerCenterY - (centerHexY * hexHeight * 0.75 + hexHeight / 2);
        const getHexCenter = (x, y) => {
            const centerX = boardOffsetX + x * hexWidth;
            const centerY = boardOffsetY + y * hexHeight * 0.75;
            return {
                x: centerX + hexWidth / 2,
                y: centerY + hexHeight / 2
            };
        };
        
        // Helper to get hex vertices (flat-top hexagon)
        const getHexVertices = (center) => ({
            top: {x: center.x, y: center.y - hexHeight/2},
            topRight: {x: center.x + hexWidth/2, y: center.y - hexHeight/4},
            bottomRight: {x: center.x + hexWidth/2, y: center.y + hexHeight/4},
            bottom: {x: center.x, y: center.y + hexHeight/2},
            bottomLeft: {x: center.x - hexWidth/2, y: center.y + hexHeight/4},
            topLeft: {x: center.x - hexWidth/2, y: center.y - hexHeight/4}
        });
        
        // Get centers for all 19 hexes using the EXACT positions from initializeBoard
        const hexes = [];
        // Row 0 (top) - 3 hexes
        hexes.push(getHexVertices(getHexCenter(2, 0)));
        hexes.push(getHexVertices(getHexCenter(3, 0)));
        hexes.push(getHexVertices(getHexCenter(4, 0)));
        // Row 1 - 4 hexes
        hexes.push(getHexVertices(getHexCenter(1.5, 1)));
        hexes.push(getHexVertices(getHexCenter(2.5, 1)));
        hexes.push(getHexVertices(getHexCenter(3.5, 1)));
        hexes.push(getHexVertices(getHexCenter(4.5, 1)));
        // Row 2 (middle) - 5 hexes
        hexes.push(getHexVertices(getHexCenter(1, 2)));
        hexes.push(getHexVertices(getHexCenter(2, 2)));
        hexes.push(getHexVertices(getHexCenter(3, 2)));  // CENTER HEX (index 9)
        hexes.push(getHexVertices(getHexCenter(4, 2)));
        hexes.push(getHexVertices(getHexCenter(5, 2)));
        // Row 3 - 4 hexes
        hexes.push(getHexVertices(getHexCenter(1.5, 3)));
        hexes.push(getHexVertices(getHexCenter(2.5, 3)));
        hexes.push(getHexVertices(getHexCenter(3.5, 3)));
        hexes.push(getHexVertices(getHexCenter(4.5, 3)));
        // Row 4 (bottom) - 3 hexes
        hexes.push(getHexVertices(getHexCenter(2, 4)));
        hexes.push(getHexVertices(getHexCenter(3, 4)));
        hexes.push(getHexVertices(getHexCenter(4, 4)));
        
        // Use Catanatron's exact node mapping based on tile processing order
        // The mapping accounts for how Catanatron assigns node IDs as it processes tiles
        this.nodePositions = {};
        
        // Load the catanatron mapping if available
        if (typeof CATANATRON_NODE_TO_HEX !== 'undefined') {
            // Use the imported mapping
            for (const [nodeId, hexVertices] of Object.entries(CATANATRON_NODE_TO_HEX)) {
                // Take the first hex/vertex combination (they all point to the same position)
                const {hex, vertex} = hexVertices[0];
                this.nodePositions[nodeId] = hexes[hex][vertex];
            }
        } else {
            // Fallback to hardcoded mapping based on our analysis
            // Node assignments based on Catanatron's tile processing order
            
            // Nodes 0-5 are the vertices of the center hex (hex 9 in our array)
            this.nodePositions[0] = hexes[9].top;
            this.nodePositions[1] = hexes[9].topRight;
            this.nodePositions[2] = hexes[9].bottomRight;
            this.nodePositions[3] = hexes[9].bottom;
            this.nodePositions[4] = hexes[9].bottomLeft;
            this.nodePositions[5] = hexes[9].topLeft;
            
            // Nodes 6-11 are new vertices when hex 1 (our hex 10) is processed
            this.nodePositions[6] = hexes[10].top;
            this.nodePositions[7] = hexes[10].topRight;
            this.nodePositions[8] = hexes[10].bottomRight;
            this.nodePositions[9] = hexes[10].bottom;
            // Node 10 and 11 are already assigned (shared with center hex)
            
            // When hex 2 (our hex 14) is processed
            this.nodePositions[10] = hexes[14].bottomRight;
            this.nodePositions[11] = hexes[14].bottom;
            this.nodePositions[12] = hexes[14].bottomLeft;
            
            // When hex 3 (our hex 13) is processed
            this.nodePositions[13] = hexes[13].bottom;
            this.nodePositions[14] = hexes[13].bottomLeft;
            this.nodePositions[15] = hexes[13].topLeft;
            
            // When hex 4 (our hex 8) is processed
            this.nodePositions[16] = hexes[8].top;
            this.nodePositions[17] = hexes[8].bottomLeft;
            this.nodePositions[18] = hexes[8].topLeft;
            
            // When hex 5 (our hex 4) is processed
            this.nodePositions[19] = hexes[4].top;
            this.nodePositions[20] = hexes[4].topRight;
            this.nodePositions[21] = hexes[4].topLeft;
            
            // When hex 6 (our hex 5) is processed
            this.nodePositions[22] = hexes[5].top;
            this.nodePositions[23] = hexes[5].topRight;
            
            // When hex 7 (our hex 11) is processed - start of outer ring
            this.nodePositions[24] = hexes[11].top;
            this.nodePositions[25] = hexes[11].topRight;
            this.nodePositions[26] = hexes[11].bottomRight;
            this.nodePositions[27] = hexes[11].bottom;
            
            // When hex 8 (our hex 15) is processed
            this.nodePositions[28] = hexes[15].bottomRight;
            this.nodePositions[29] = hexes[15].bottom;
            
            // When hex 9 (our hex 18) is processed
            this.nodePositions[30] = hexes[18].bottomRight;
            this.nodePositions[31] = hexes[18].bottom;
            this.nodePositions[32] = hexes[18].bottomLeft;
            
            // When hex 10 (our hex 17) is processed
            this.nodePositions[33] = hexes[17].bottom;
            this.nodePositions[34] = hexes[17].bottomLeft;
            
            // When hex 11 (our hex 16) is processed
            this.nodePositions[35] = hexes[16].bottom;
            this.nodePositions[36] = hexes[16].bottomLeft;
            this.nodePositions[37] = hexes[16].topLeft;
            
            // When hex 12 (our hex 12) is processed
            this.nodePositions[38] = hexes[12].bottomLeft;
            this.nodePositions[39] = hexes[12].topLeft;
            
            // When hex 13 (our hex 7) is processed
            this.nodePositions[40] = hexes[7].top;
            this.nodePositions[41] = hexes[7].bottomLeft;
            this.nodePositions[42] = hexes[7].topLeft;
            
            // When hex 14 (our hex 3) is processed
            this.nodePositions[43] = hexes[3].top;
            this.nodePositions[44] = hexes[3].topLeft;
            
            // When hex 15 (our hex 0) is processed
            this.nodePositions[45] = hexes[0].top;
            this.nodePositions[46] = hexes[0].topRight;
            this.nodePositions[47] = hexes[0].topLeft;
            
            // When hex 16 (our hex 1) is processed
            this.nodePositions[48] = hexes[1].top;
            this.nodePositions[49] = hexes[1].topRight;
            
            // When hex 17 (our hex 2) is processed
            this.nodePositions[50] = hexes[2].top;
            this.nodePositions[51] = hexes[2].topRight;
            this.nodePositions[52] = hexes[2].bottomRight;
            
            // When hex 18 (our hex 6) is processed
            this.nodePositions[53] = hexes[6].topRight;
        }
        
        console.log('Node positions calculated:', Object.keys(this.nodePositions).length);
    }
    
    
    _removed_showAllEdges() {
        // Show all valid edges according to Catanatron
        const boardDisplay = document.getElementById('board-display');
        
        // Remove existing edge debug lines
        const existingEdges = boardDisplay.querySelectorAll('.edge-debug');
        existingEdges.forEach(edge => edge.remove());
        
        // Only show if debug mode is enabled
        if (!this.showDebugNodes) return;
        
        // Catanatron's valid edges (from our analysis)
        const validEdges = [
            [0,1], [0,5], [0,20], [1,2], [1,6], [2,3], [2,9], [3,4], [3,12], [4,5],
            [4,15], [5,16], [6,7], [6,23], [7,8], [7,24], [8,9], [8,27], [9,10], [10,11],
            [10,29], [11,12], [11,32], [12,13], [13,14], [13,34], [14,15], [14,37], [15,17], [16,18],
            [16,21], [17,18], [17,39], [18,40], [19,20], [19,21], [19,46], [20,22], [21,43], [22,23],
            [22,49], [23,52], [24,25], [24,53], [25,26], [26,27], [27,28], [28,29], [29,30], [30,31],
            [31,32], [32,33], [33,34], [34,35], [35,36], [36,37], [37,38], [38,39], [39,41], [40,42],
            [40,44], [41,42], [43,44], [43,47], [45,46], [45,47], [46,48], [48,49], [49,50], [50,51],
            [51,52], [52,53]
        ];
        
        // Draw each edge
        validEdges.forEach(edge => {
            const [node1, node2] = edge;
            const pos1 = this.nodePositions[node1];
            const pos2 = this.nodePositions[node2];
            
            if (!pos1 || !pos2) return;
            
            const line = document.createElement('div');
            line.className = 'edge-debug';
            line.style.position = 'absolute';
            
            const dx = pos2.x - pos1.x;
            const dy = pos2.y - pos1.y;
            const length = Math.sqrt(dx * dx + dy * dy);
            const angle = Math.atan2(dy, dx) * 180 / Math.PI;
            
            line.style.width = `${length}px`;
            line.style.height = '1px';
            line.style.left = `${pos1.x}px`;
            line.style.top = `${pos1.y}px`;
            line.style.transformOrigin = '0 50%';
            line.style.transform = `rotate(${angle}deg)`;
            line.style.backgroundColor = 'rgba(0, 0, 0, 0.3)';
            line.style.zIndex = '1';
            
            // Highlight the problematic edge
            if ((node1 === 7 && node2 === 24) || (node1 === 24 && node2 === 7)) {
                line.style.backgroundColor = 'red';
                line.style.height = '3px';
                line.style.zIndex = '100';
            }
            
            boardDisplay.appendChild(line);
        });
    }
    
    showNodeDebug() {
        const boardDisplay = document.getElementById('board-display');
        Object.entries(this.nodePositions).forEach(([nodeId, pos]) => {
            const marker = document.createElement('div');
            marker.style.position = 'absolute';
            marker.style.left = `${pos.x - 10}px`;
            marker.style.top = `${pos.y - 10}px`;
            marker.style.width = '20px';
            marker.style.height = '20px';
            marker.style.borderRadius = '50%';
            marker.style.backgroundColor = 'rgba(255, 0, 0, 0.5)';
            marker.style.fontSize = '10px';
            marker.style.display = 'flex';
            marker.style.alignItems = 'center';
            marker.style.justifyContent = 'center';
            marker.style.color = 'white';
            marker.style.fontWeight = 'bold';
            marker.style.zIndex = '100';
            marker.textContent = nodeId;
            boardDisplay.appendChild(marker);
        });
    }

    updateGame(gameId, actionData) {
        if (gameId !== this.currentGameId) return;
        
        // Update game state
        if (actionData.game_state) {
            const state = actionData.game_state;
            
            // Update turn and phase
            const turnDisplay = document.getElementById('current-turn-display');
            const turn = state.turn || 0;
            
            // First 8 turns are initial build phase (2 settlements + 2 roads per player)
            if (turn < 8) {
                turnDisplay.innerHTML = `Turn ${turn} <span style="color: #f39c12; font-size: 0.8em;">(Initial Build Phase)</span>`;
            } else {
                turnDisplay.textContent = `Turn ${turn}`;
            }
            
            // Highlight active player
            const currentPlayer = state.current_player_color;
            document.querySelectorAll('.player-panel').forEach(panel => {
                panel.classList.remove('active');
            });
            if (currentPlayer) {
                const activePanel = document.querySelector(`.player-${currentPlayer.toLowerCase()}`);
                if (activePanel) {
                    activePanel.classList.add('active');
                }
            }
            
            // Update scores and resources
            if (state.players) {
                this.updatePlayerState('red', state.players.RED);
                this.updatePlayerState('blue', state.players.BLUE);
            }
            
            // Update board if we have board data
            if (state.board) {
                this.updateBoard(state.board);
            }
        }
        
        // Add action to log
        this.addAction(actionData);
    }

    updatePlayerState(color, playerData) {
        if (!playerData) return;
        
        // Update score
        const scoreElem = document.getElementById(`${color}-score`);
        if (scoreElem) {
            scoreElem.textContent = playerData.victory_points || 0;
        }
        
        // Update resources in the new container
        const resourcesElem = document.getElementById(`${color}-resources`);
        if (resourcesElem && playerData.resources) {
            resourcesElem.innerHTML = this.formatResources(playerData.resources);
        }
        
        // Update buildings info
        const buildingsElem = document.getElementById(`${color}-buildings`);
        if (buildingsElem) {
            const settlements = playerData.settlements || 0;
            const cities = playerData.cities || 0;
            const roads = playerData.roads || 0;
            let buildingText = `🏠 ${settlements} 🏛️ ${cities} 🛤️ ${roads}`;
            
            // Add longest road indicator if player has it (5+ roads)
            if (roads >= 5) {
                buildingText += ` (Longest: ${roads})`;
            }
            
            buildingsElem.textContent = buildingText;
            
            // Show port access if player has any
            if (this.boardState && this.boardState.ports && this.boardState.buildings) {
                const playerPorts = [];
                this.boardState.buildings.forEach(building => {
                    if (building.color.toLowerCase() === color && building.type === 'settlement') {
                        // Check if this settlement is on a port
                        const portAtNode = this.boardState.ports.find(p => p.node_id === building.node_id);
                        if (portAtNode && !playerPorts.includes(portAtNode.type)) {
                            playerPorts.push(portAtNode.type);
                        }
                    }
                });
                
                if (playerPorts.length > 0) {
                    buildingText += ' | Ports: ';
                    playerPorts.forEach(portType => {
                        if (portType.includes('WOOD')) buildingText += '🪵 ';
                        else if (portType.includes('BRICK')) buildingText += '🧱 ';
                        else if (portType.includes('SHEEP')) buildingText += '🐑 ';
                        else if (portType.includes('WHEAT')) buildingText += '🌾 ';
                        else if (portType.includes('ORE')) buildingText += '⛏️ ';
                        else if (portType.includes('THREE_TO_ONE') || portType.includes('ANY')) buildingText += '3:1 ';
                    });
                    buildingsElem.textContent = buildingText.trim();
                }
            }
        }
    }

    formatResources(resources) {
        const resourceIcons = {
            wood: '🪵',
            brick: '🧱', 
            sheep: '🐑',
            wheat: '🌾',
            ore: '⛏️'
        };
        
        let html = '';
        for (const [type, count] of Object.entries(resources)) {
            html += `
                <div class="resource-card ${type}" style="${count === 0 ? 'opacity: 0.5;' : ''}">
                    <div class="resource-icon">${resourceIcons[type]}</div>
                    <div class="resource-count">${count}</div>
                </div>
            `;
        }
        
        return html || '<div style="opacity: 0.5;">No resources</div>';
    }
    
    updateBoard(boardData) {
        if (!boardData || !boardData.hexes) return;
        
        this.boardState = boardData;
        
        // Update each hex with actual data from Catanatron
        boardData.hexes.forEach(hexData => {
            const hexElement = this.hexElements[hexData.coordinate];
            if (!hexElement) return;
            
            // Clear existing classes
            hexElement.className = 'hex-tile';
            
            // Add resource class
            const resource = hexData.resource || 'desert';
            hexElement.classList.add(`hex-${resource}`);
            
            // Update center content (number or robber)
            const centerDiv = hexElement.querySelector('.hex-center');
            if (centerDiv) {
                centerDiv.innerHTML = '';
                
                if (hexData.cube_coord === boardData.robber) {
                    // This hex has the robber
                    const robber = document.createElement('div');
                    robber.className = 'robber';
                    robber.textContent = '🏴';
                    centerDiv.appendChild(robber);
                } else if (hexData.number) {
                    // This hex has a number (desert tiles won't have numbers)
                    const numberDiv = document.createElement('div');
                    numberDiv.className = 'hex-number';
                    
                    // Add special styling for high probability numbers
                    if (hexData.number === 6 || hexData.number === 8) {
                        numberDiv.classList.add('high-probability');
                    }
                    numberDiv.textContent = hexData.number;
                    centerDiv.appendChild(numberDiv);
                    
                    // Add probability dots
                    const dotsContainer = document.createElement('div');
                    dotsContainer.className = 'probability-dots';
                    
                    // Determine number of dots based on probability
                    let dotCount = 0;
                    switch(hexData.number) {
                        case 2:
                        case 12:
                            dotCount = 1;
                            break;
                        case 3:
                        case 11:
                            dotCount = 2;
                            break;
                        case 4:
                        case 10:
                            dotCount = 3;
                            break;
                        case 5:
                        case 9:
                            dotCount = 4;
                            break;
                        case 6:
                        case 8:
                            dotCount = 5;
                            break;
                    }
                    
                    // Create dots
                    for (let i = 0; i < dotCount; i++) {
                        const dot = document.createElement('div');
                        dot.className = 'probability-dot';
                        dotsContainer.appendChild(dot);
                    }
                    
                    centerDiv.appendChild(dotsContainer);
                }
            }
        });
        
        // Update buildings, roads, and ports
        console.log('Board data buildings:', boardData.buildings);
        console.log('Board data roads:', boardData.roads);
        console.log('Board data ports:', boardData.ports);
        this.updateBuildings(boardData.buildings || []);
        this.updateRoads(boardData.roads || []);
        this.updatePorts(boardData.ports || []);
    }

    addAction(actionData) {
        const actionsList = document.getElementById('actions-list');
        const actionClass = actionData.player === 'BLUE' ? 'blue-action' : '';
        
        // Format action text
        let actionText = actionData.action
            .replace(/Action\([A-Z]+ /, '')
            .replace(/\)$/, '')
            .replace(/_/g, ' ')
            .toLowerCase();
        
        // Format reasoning
        let reasoningHtml = '';
        if (actionData.reasoning) {
            const isAutoMove = actionData.reasoning === 'AUTO MOVE';
            const reasoningClass = isAutoMove ? 'auto-move' : 'llm-reasoning';
            const reasoningIcon = isAutoMove ? '⚡' : '💭';
            reasoningHtml = `
                <div class="action-reasoning ${reasoningClass}">
                    <span class="reasoning-icon">${reasoningIcon}</span>
                    <span class="reasoning-text">${isAutoMove ? 'AUTO MOVE' : actionData.reasoning}</span>
                </div>
            `;
        }
        
        const actionHtml = `
            <div class="action-item ${actionClass}">
                <div class="action-header">
                    <strong>${actionData.player}</strong>: ${actionText}
                </div>
                ${reasoningHtml}
            </div>
        `;
        
        // Add to top of list
        actionsList.insertAdjacentHTML('afterbegin', actionHtml);
        
        // Keep only last 20 actions
        while (actionsList.children.length > 20) {
            actionsList.removeChild(actionsList.lastChild);
        }
    }

    updateBuildings(buildings) {
        console.log('Updating buildings:', buildings);
        console.log('Node positions available:', Object.keys(this.nodePositions).length);
        
        // Remove existing buildings
        const existingBuildings = document.querySelectorAll('.building');
        existingBuildings.forEach(b => b.remove());
        
        const boardDisplay = document.getElementById('board-display');
        
        // Draw each building
        buildings.forEach(building => {
            console.log('Building node_id:', building.node_id);
            const position = this.nodePositions[building.node_id];
            console.log('Position for node', building.node_id, ':', position);
            if (!position) return;
            
            const buildingEl = document.createElement('div');
            buildingEl.className = `building ${building.type} ${building.color.toLowerCase()}`;
            buildingEl.style.position = 'absolute';
            buildingEl.style.zIndex = '50';  // Higher z-index to ensure buildings are on top of roads
            
            // Create colored shapes instead of emojis
            if (building.type === 'settlement') {
                buildingEl.style.width = '20px';
                buildingEl.style.height = '20px';
                buildingEl.style.borderRadius = '4px';
                buildingEl.style.left = `${position.x - 10}px`;  // Center 20px building
                buildingEl.style.top = `${position.y - 10}px`;
            } else {
                buildingEl.style.width = '24px';
                buildingEl.style.height = '24px';
                buildingEl.style.borderRadius = '50%';
                buildingEl.style.left = `${position.x - 12}px`;  // Center 24px building
                buildingEl.style.top = `${position.y - 12}px`;
            }
            
            // Add color styling
            console.log('Building color:', building.color);
            if (building.color === 'RED') {
                buildingEl.style.backgroundColor = '#dc3545';
                buildingEl.style.border = '2px solid #a02532';
            } else if (building.color === 'BLUE') {
                buildingEl.style.backgroundColor = '#007bff';
                buildingEl.style.border = '2px solid #0056b3';
            } else {
                // Log unexpected color
                console.warn('Unexpected building color:', building.color);
                buildingEl.style.backgroundColor = '#6c757d';
                buildingEl.style.border = '2px solid #495057';
            }
            
            boardDisplay.appendChild(buildingEl);
        });
    }
    
    updateRoads(roads) {
        // Remove existing roads
        const existingRoads = document.querySelectorAll('.road');
        existingRoads.forEach(r => r.remove());
        
        const boardDisplay = document.getElementById('board-display');
        
        // Draw each road
        roads.forEach(road => {
            // Roads connect two nodes
            let node1, node2;
            if (Array.isArray(road.edge) && road.edge.length === 2) {
                // Extract node IDs from the edge format
                // Edge format might be like ["(16, 8)", "(8, 0)"] or just [16, 8]
                node1 = this.extractNodeId(road.edge[0]);
                node2 = this.extractNodeId(road.edge[1]);
            }
            
            console.log(`Road connecting nodes ${node1} to ${node2}, color: ${road.color}`);
            
            if (node1 === null || node2 === null) return;
            
            const pos1 = this.nodePositions[node1];
            const pos2 = this.nodePositions[node2];
            if (!pos1 || !pos2) return;
            
            // Create road as a line
            const road_el = document.createElement('div');
            road_el.className = `road ${road.color.toLowerCase()}`;
            road_el.style.position = 'absolute';
            
            // Calculate road position and angle
            const dx = pos2.x - pos1.x;
            const dy = pos2.y - pos1.y;
            const length = Math.sqrt(dx * dx + dy * dy);
            const angle = Math.atan2(dy, dx) * 180 / Math.PI;
            
            road_el.style.width = `${length}px`;
            road_el.style.height = '8px';
            road_el.style.left = `${pos1.x}px`;
            road_el.style.top = `${pos1.y}px`;
            road_el.style.transformOrigin = '0 50%';
            road_el.style.transform = `rotate(${angle}deg) translateY(-50%)`;
            
            // Color the road
            if (road.color === 'RED') {
                road_el.style.backgroundColor = '#dc3545';
            } else if (road.color === 'BLUE') {
                road_el.style.backgroundColor = '#007bff';
            } else {
                console.warn('Unexpected road color:', road.color);
                road_el.style.backgroundColor = '#6c757d';
            }
            
            road_el.style.borderRadius = '4px';
            road_el.style.zIndex = '1';
            
            boardDisplay.appendChild(road_el);
        });
    }
    
    updatePorts(ports) {
        // Remove existing ports and SVG elements
        const existingPorts = document.querySelectorAll('.port-marker, .port-svg');
        existingPorts.forEach(p => p.remove());
        
        if (!ports || ports.length === 0) return;
        
        const boardDisplay = document.getElementById('board-display');
        const hexSideLength = 45; // Reduced to keep ports within canvas bounds
        
        // Hardcoded port pairs from Catanatron debug output
        const PORT_PAIRS = [
            {nodes: [25, 26], type: '3:1'},
            {nodes: [28, 29], type: 'ORE'},
            {nodes: [32, 33], type: 'WHEAT'},
            {nodes: [35, 36], type: 'WOOD'},
            {nodes: [38, 39], type: '3:1'},
            {nodes: [40, 44], type: 'BRICK'},
            {nodes: [45, 47], type: '3:1'},
            {nodes: [48, 49], type: '3:1'},
            {nodes: [52, 53], type: 'SHEEP'}
        ];
        
        // Create a map from port nodes to their types
        const nodeToType = {};
        ports.forEach(port => {
            nodeToType[port.node_id] = port.type || 'THREE_TO_ONE';
        });
        
        // Debug: log what ports we have
        console.log('Port nodes from server:', ports);
        console.log('Port node IDs:', ports.map(p => p.node_id).sort((a,b) => a-b));
        console.log('Node to type mapping:', nodeToType);
        
        // Check which port nodes have positions
        const missingPositions = [];
        ports.forEach(port => {
            if (!this.nodePositions[port.node_id]) {
                missingPositions.push(port.node_id);
            }
        });
        if (missingPositions.length > 0) {
            console.warn('Port nodes missing positions:', missingPositions);
        }
        
        // Let's also check which of our hardcoded pairs actually have ports
        const validPairs = [];
        
        // Track which ports we successfully draw
        const drawnPorts = [];
        const skippedPorts = [];
        
        // Process each hardcoded port pair
        PORT_PAIRS.forEach(portPair => {
            const [node1Id, node2Id] = portPair.nodes;
            const portType = portPair.type;
            
            console.log(`Processing port pair [${node1Id}, ${node2Id}] of type ${portType}`);
            
            const node1 = this.nodePositions[node1Id];
            const node2 = this.nodePositions[node2Id];
            
            if (!node1 || !node2) {
                console.warn(`Missing position for port nodes ${node1Id} or ${node2Id}`);
                skippedPorts.push([node1Id, node2Id]);
                return;
            }
            
            // Draw the port
            this.drawPort(node1, node2, node1Id, node2Id, portType, hexSideLength, boardDisplay);
            drawnPorts.push([node1Id, node2Id]);
        });
        
        // Summary
        console.log(`Successfully drew ${drawnPorts.length} ports:`, drawnPorts);
        console.log(`Skipped ${skippedPorts.length} ports:`, skippedPorts);
    }
    
    drawPort(node1, node2, node1Id, node2Id, type, hexSideLength, boardDisplay) {
        // Calculate edge properties
        const edgeDx = node2.x - node1.x;
        const edgeDy = node2.y - node1.y;
            const edgeLength = Math.sqrt(edgeDx * edgeDx + edgeDy * edgeDy);
            
            // Calculate midpoint of the edge
            const midX = (node1.x + node2.x) / 2;
            const midY = (node1.y + node2.y) / 2;
            
            // Calculate perpendicular direction (normalized)
            const perpX = -edgeDy / edgeLength;
            const perpY = edgeDx / edgeLength;
            
            // Determine which direction to go (outward from board center)
            const boardCenterX = 300;
            const boardCenterY = 285;
            const toCenterX = boardCenterX - midX;
            const toCenterY = boardCenterY - midY;
            
            // Check if perpendicular points away from center
            const dotProduct = perpX * toCenterX + perpY * toCenterY;
            const direction = dotProduct > 0 ? -1 : 1;
            
            // Place port at hex side length distance
            const portX = midX + direction * perpX * hexSideLength;
            const portY = midY + direction * perpY * hexSideLength;
            
            // Get or create the main SVG for port lines
            let svg = boardDisplay.querySelector('#port-lines-svg');
            if (!svg) {
                svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                svg.id = 'port-lines-svg';
                svg.style.position = 'absolute';
                svg.style.left = '-85px';
                svg.style.top = '-85px';
                svg.style.width = '700px';
                svg.style.height = '700px';
                svg.style.pointerEvents = 'none';
                svg.style.zIndex = '14';
                svg.style.overflow = 'visible';
                svg.setAttribute('viewBox', '-85 -85 700 700');
                boardDisplay.appendChild(svg);
            }
            
            // Draw line from node1 to port
            const line1 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line1.setAttribute('x1', node1.x);
            line1.setAttribute('y1', node1.y);
            line1.setAttribute('x2', portX);
            line1.setAttribute('y2', portY);
            line1.setAttribute('stroke', 'white');
            line1.setAttribute('stroke-width', '3');
            line1.setAttribute('opacity', '0.9');
            svg.appendChild(line1);
            
            // Draw line from node2 to port
            const line2 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line2.setAttribute('x1', node2.x);
            line2.setAttribute('y1', node2.y);
            line2.setAttribute('x2', portX);
            line2.setAttribute('y2', portY);
            line2.setAttribute('stroke', 'white');
            line2.setAttribute('stroke-width', '3');
            line2.setAttribute('opacity', '0.9');
            svg.appendChild(line2);
            
            // Create port indicator
            const portEl = document.createElement('div');
            portEl.className = 'port-marker';
            portEl.style.position = 'absolute';
            portEl.style.left = `${portX - 20}px`;
            portEl.style.top = `${portY - 20}px`;
            portEl.style.width = '40px';
            portEl.style.height = '40px';
            portEl.style.borderRadius = '50%';
            portEl.style.backgroundColor = 'white';
            portEl.style.border = '3px solid #333';
            portEl.style.display = 'flex';
            portEl.style.alignItems = 'center';
            portEl.style.justifyContent = 'center';
            portEl.style.fontSize = '18px';
            portEl.style.fontWeight = 'bold';
            portEl.style.color = '#333';
            portEl.style.zIndex = '15';
            portEl.style.cursor = 'help';
            portEl.style.boxShadow = '0 3px 6px rgba(0, 0, 0, 0.3)';
            
            // Set port content based on type
            if (type === 'WOOD') {
                portEl.innerHTML = '🪵';
                portEl.title = 'Wood Port (2:1)';
            } else if (type === 'BRICK') {
                portEl.innerHTML = '🧱';
                portEl.title = 'Brick Port (2:1)';
            } else if (type === 'SHEEP') {
                portEl.innerHTML = '🐑';
                portEl.title = 'Sheep Port (2:1)';
            } else if (type === 'WHEAT') {
                portEl.innerHTML = '🌾';
                portEl.title = 'Wheat Port (2:1)';
            } else if (type === 'ORE') {
                portEl.innerHTML = '⛏️';
                portEl.title = 'Ore Port (2:1)';
            } else {
                // 3:1 port
                portEl.textContent = '3:1';
                portEl.style.fontSize = '16px';
                portEl.title = 'General Port (3:1)';
            }
            
            boardDisplay.appendChild(portEl);
    }
    
    
    extractNodeId(edgeStr) {
        // Try to extract node ID from various formats
        console.log('Extracting node from:', edgeStr);
        if (typeof edgeStr === 'number') return edgeStr;
        if (typeof edgeStr === 'string') {
            // The edge strings are just node numbers as strings
            const nodeId = parseInt(edgeStr);
            if (!isNaN(nodeId)) return nodeId;
            
            // If that didn't work, try to match any number
            const match = edgeStr.match(/\d+/);
            return match ? parseInt(match[0]) : null;
        }
        return null;
    }

    endGame() {
        // Show waiting state again
        document.getElementById('waiting-state').style.display = 'flex';
        document.getElementById('game-state').style.display = 'none';
        this.currentGameId = null;
    }

    setupEventListeners() {
        
        // Handle page visibility changes (when coming back from stats page)
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && !this.currentGameId) {
                console.log('Page became visible, checking for active game...');
                this.checkForActiveGame();
            }
        });
    }
    
    _removed_addDebugToggle() {
        const debugButton = document.createElement('button');
        debugButton.id = 'debug-toggle';
        debugButton.innerHTML = '🔧 Debug: OFF';
        debugButton.style.position = 'fixed';
        debugButton.style.bottom = '20px';
        debugButton.style.right = '20px';
        debugButton.style.padding = '10px 20px';
        debugButton.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
        debugButton.style.color = 'white';
        debugButton.style.border = 'none';
        debugButton.style.borderRadius = '5px';
        debugButton.style.cursor = 'pointer';
        debugButton.style.zIndex = '2000';
        debugButton.style.fontSize = '14px';
        
        debugButton.onclick = () => this._removed_toggleDebugMode();
        document.body.appendChild(debugButton);
    }
    
    _removed_toggleDebugMode() {
        this.showDebugNodes = !this.showDebugNodes;
        const button = document.getElementById('debug-toggle');
        button.innerHTML = this.showDebugNodes ? '🔧 Debug: ON' : '🔧 Debug: OFF';
        
        // Toggle edge display if they exist
        const edgeDebugElements = document.querySelectorAll('.edge-debug');
        edgeDebugElements.forEach(edge => {
            edge.style.display = this.showDebugNodes ? 'block' : 'none';
        });
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new CatanDashboard();
});