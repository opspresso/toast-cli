document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle
    const hamburger = document.querySelector('.hamburger');
    const navLinks = document.querySelector('.nav-links');

    if (hamburger) {
        hamburger.addEventListener('click', function() {
            navLinks.classList.toggle('active');
        });
    }

    // Architecture diagram elements and connectors
    // 다이어그램 요소 정의
    const diagramElements = {
        // 제목
        'title': {
            type: 'title',
            content: [
                { type: 'text', x: 400, y: 40, fontFamily: 'Arial', fontSize: 24, textAnchor: 'middle', fontWeight: 'bold', text: 'Toast-cli Architecture' },
                { type: 'text', x: 400, y: 70, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', fill: '#6c757d', text: 'Plugin-based Design Pattern v3.1.0' }
            ]
        },
        // 메인 CLI 박스
        'main-cli': {
            type: 'box',
            rect: { x: 200, y: 100, width: 400, height: 80, rx: 10, fill: '#e9f5ff', stroke: '#007bff', strokeWidth: 2 },
            content: [
                { type: 'text', x: 400, y: 145, fontFamily: 'Arial', fontSize: 18, textAnchor: 'middle', text: 'Main CLI Application' },
                { type: 'text', x: 400, y: 165, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', fill: '#6c757d', text: '(toast/__init__.py)' }
            ]
        },
        // BasePlugin 박스
        'base-plugin': {
            type: 'box',
            rect: { x: 250, y: 230, width: 300, height: 70, rx: 10, fill: '#e9f5ff', stroke: '#007bff', strokeWidth: 2 },
            content: [
                { type: 'text', x: 400, y: 270, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', text: 'BasePlugin' },
                { type: 'text', x: 400, y: 290, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '(toast/plugins/base_plugin.py)' }
            ]
        },
        // 플러그인 행 1
        'am-plugin': {
            type: 'box',
            rect: { x: 50, y: 350, width: 140, height: 50, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
            content: [
                { type: 'text', x: 120, y: 380, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', text: 'am_plugin.py' }
            ]
        },
        'ctx-plugin': {
            type: 'box',
            rect: { x: 200, y: 350, width: 140, height: 50, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
            content: [
                { type: 'text', x: 270, y: 380, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', text: 'ctx_plugin.py' }
            ]
        },
        'env-plugin': {
            type: 'box',
            rect: { x: 350, y: 350, width: 140, height: 50, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
            content: [
                { type: 'text', x: 420, y: 380, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', text: 'env_plugin.py' }
            ]
        },
        'git-plugin': {
            type: 'box',
            rect: { x: 500, y: 350, width: 140, height: 50, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
            content: [
                { type: 'text', x: 570, y: 380, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', text: 'git_plugin.py' }
            ]
        },
        'utils': {
            type: 'box',
            rect: { x: 650, y: 350, width: 100, height: 50, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
            content: [
                { type: 'text', x: 700, y: 380, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', text: 'utils.py' }
            ]
        },
        // 플러그인 행 2
        'cdw-plugin': {
            type: 'box',
            rect: { x: 50, y: 410, width: 140, height: 50, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
            content: [
                { type: 'text', x: 120, y: 440, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', text: 'cdw_plugin.py' }
            ]
        },
        'dot-plugin': {
            type: 'box',
            rect: { x: 200, y: 410, width: 140, height: 50, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
            content: [
                { type: 'text', x: 270, y: 440, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', text: 'dot_plugin.py' }
            ]
        },
        'region-plugin': {
            type: 'box',
            rect: { x: 350, y: 410, width: 140, height: 50, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
            content: [
                { type: 'text', x: 420, y: 440, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', text: 'region_plugin.py' }
            ]
        },
        // 플러그인 명령 박스
        'plugin-commands': {
            type: 'box',
            rect: { x: 150, y: 490, width: 500, height: 70, rx: 6, fill: '#f8f9fa', stroke: '#6c757d', strokeWidth: 1 },
            content: [
                { type: 'text', x: 400, y: 515, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', fontWeight: 'bold', text: 'Plugin Commands' },
                { type: 'text', x: 400, y: 540, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: 'am | cdw | ctx | dot | env | git | region | version' }
            ]
        },
        // 외부 의존성 박스
        'dependencies': {
            type: 'box',
            rect: { x: 40, y: 100, width: 130, height: 180, rx: 6, fill: '#f8f9fa', stroke: '#6c757d', strokeWidth: 1, strokeDasharray: '5,3' },
            content: [
                { type: 'text', x: 105, y: 125, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', fontWeight: 'bold', text: 'Dependencies' },
                { type: 'text', x: 105, y: 150, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '• Click' },
                { type: 'text', x: 105, y: 170, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '• importlib' },
                { type: 'text', x: 105, y: 190, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '• pkgutil' },
                { type: 'text', x: 105, y: 210, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '• fzf' },
                { type: 'text', x: 105, y: 230, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '• jq' },
                { type: 'text', x: 105, y: 250, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '• aws-cli' },
                { type: 'text', x: 105, y: 270, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '• kubectl' }
            ]
        },
        // 외부 도구 박스
        'ui': {
            type: 'box',
            rect: { x: 630, y: 100, width: 130, height: 180, rx: 6, fill: '#f8f9fa', stroke: '#6c757d', strokeWidth: 1, strokeDasharray: '5,3' },
            content: [
                { type: 'text', x: 695, y: 125, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', fontWeight: 'bold', text: 'User Interface' },
                { type: 'text', x: 695, y: 150, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '• CLI commands' },
                { type: 'text', x: 695, y: 170, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '• Interactive' },
                { type: 'text', x: 695, y: 190, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '  selection (fzf)' },
                { type: 'text', x: 695, y: 210, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '• Colorized JSON' },
                { type: 'text', x: 695, y: 230, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '  output (jq)' },
                { type: 'text', x: 695, y: 250, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '• Custom help' }
            ]
        },
        // 통합 박스
        'integration': {
            type: 'box',
            rect: { x: 500, y: 410, width: 250, height: 50, rx: 6, fill: '#f8f9fa', stroke: '#28a745', strokeWidth: 1 },
            content: [
                { type: 'text', x: 625, y: 440, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', fill: '#28a745', text: 'AWS SSM Parameter Store Integration' }
            ]
        },
        // 범례
        'legend': {
            type: 'legend',
            content: [
                { type: 'rect', x: 200, y: 563, width: 15, height: 15, rx: 2, fill: '#e9f5ff', stroke: '#007bff', strokeWidth: 1 },
                { type: 'text', x: 225, y: 575, fontFamily: 'Arial', fontSize: 12, text: 'Core Components' },
                { type: 'rect', x: 335, y: 563, width: 15, height: 15, rx: 2, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
                { type: 'text', x: 360, y: 575, fontFamily: 'Arial', fontSize: 12, text: 'Plugins' },
                { type: 'rect', x: 450, y: 563, width: 15, height: 15, rx: 2, fill: '#f8f9fa', stroke: '#6c757d', strokeWidth: 1, strokeDasharray: '5,3' },
                { type: 'text', x: 475, y: 575, fontFamily: 'Arial', fontSize: 12, text: 'External' },
                { type: 'rect', x: 565, y: 563, width: 15, height: 15, rx: 2, fill: '#f8f9fa', stroke: '#28a745', strokeWidth: 1 },
                { type: 'text', x: 590, y: 575, fontFamily: 'Arial', fontSize: 12, text: 'Integrations' }
            ]
        }
    };

    // 연결선 정의
    const diagramConnectors = [
        // 메인 CLI에서 BasePlugin으로
        { from: 'main-cli', to: 'base-plugin', path: 'M400,180 C400,200 400,210 400,230', stroke: '#007bff', strokeWidth: 2, fill: 'none' },

        // BasePlugin에서 플러그인 행으로
        { from: 'base-plugin', to: 'env-plugin', path: 'M400,300 C400,315 400,330 400,345', stroke: '#007bff', strokeWidth: 2, fill: 'none' },
        { from: 'base-plugin', to: 'am-plugin', path: 'M400,325 C300,325 200,325 120,325 C120,330 120,335 120,345', stroke: '#007bff', strokeWidth: 2, fill: 'none' },
        { from: 'base-plugin', to: 'utils', path: 'M400,325 C500,325 600,325 700,325 C700,330 700,335 700,345', stroke: '#007bff', strokeWidth: 2, fill: 'none' },

        // 플러그인 행 1에서 행 2로 연결
        { from: 'am-plugin', to: 'cdw-plugin', path: 'M120,400 C120,403 120,407 120,410', stroke: '#007bff', strokeWidth: 1, fill: 'none' },
        { from: 'ctx-plugin', to: 'dot-plugin', path: 'M270,400 C270,403 270,407 270,410', stroke: '#007bff', strokeWidth: 1, fill: 'none' },
        { from: 'env-plugin', to: 'region-plugin', path: 'M420,400 C420,403 420,407 420,410', stroke: '#007bff', strokeWidth: 1, fill: 'none' },
        { from: 'git-plugin', to: 'integration', path: 'M570,400 C570,403 570,407 570,410 C585,410 600,410 625,410', stroke: '#007bff', strokeWidth: 1, strokeDasharray: '4,2', fill: 'none' },

        // 플러그인에서 명령으로 연결
        { from: 'region-plugin', to: 'plugin-commands', path: 'M400,465 C400,470 400,480 400,485', stroke: '#6c757d', strokeWidth: 1, strokeDasharray: '4,2', fill: 'none' },

        // 외부 의존성에서 메인 CLI로
        { from: 'dependencies', to: 'main-cli', path: 'M170,140 C180,140 185,140 195,140', stroke: '#6c757d', strokeWidth: 1, strokeDasharray: '4,2', fill: 'none' },

        // 메인 CLI에서 UI로
        { from: 'main-cli', to: 'ui', path: 'M600,140 C610,140 615,140 625,140', stroke: '#6c757d', strokeWidth: 1, strokeDasharray: '4,2', fill: 'none' }
    ];

    // Architecture diagram drag functionality
    const interactiveDiagram = document.querySelector('.interactive-diagram');
    if (interactiveDiagram) {
        // 초기 SVG 요소 위치 저장을 위한 객체
        const initialPositions = {};
        // 현재 드래그 중인 요소
        let selectedElement = null;
        // 드래그 오프셋
        let offset = { x: 0, y: 0 };
        // 연결선 정보 저장
        const connections = {};

        // SVG 네임스페이스
        const SVG_NS = 'http://www.w3.org/2000/svg';

        // 다이어그램 요소 생성 함수
        function createDiagramElements() {
            // 모든 요소 생성
            for (const [id, element] of Object.entries(diagramElements)) {
                const group = document.createElementNS(SVG_NS, 'g');
                group.classList.add('diagram-element');
                group.setAttribute('data-element-type', element.type);
                group.setAttribute('data-element-id', id);

                // 박스 요소 생성
                if (element.rect) {
                    const rect = document.createElementNS(SVG_NS, 'rect');
                    rect.setAttribute('x', element.rect.x);
                    rect.setAttribute('y', element.rect.y);
                    rect.setAttribute('width', element.rect.width);
                    rect.setAttribute('height', element.rect.height);
                    rect.setAttribute('rx', element.rect.rx);
                    rect.setAttribute('fill', element.rect.fill);
                    rect.setAttribute('stroke', element.rect.stroke);
                    rect.setAttribute('stroke-width', element.rect.strokeWidth);
                    if (element.rect.strokeDasharray) {
                        rect.setAttribute('stroke-dasharray', element.rect.strokeDasharray);
                    }
                    group.appendChild(rect);
                }

                // 내용 요소 생성
                if (element.content) {
                    element.content.forEach(item => {
                        if (item.type === 'text') {
                            const text = document.createElementNS(SVG_NS, 'text');
                            text.setAttribute('x', item.x);
                            text.setAttribute('y', item.y);
                            text.setAttribute('font-family', item.fontFamily);
                            text.setAttribute('font-size', item.fontSize);
                            text.setAttribute('text-anchor', item.textAnchor);
                            if (item.fontWeight) {
                                text.setAttribute('font-weight', item.fontWeight);
                            }
                            if (item.fill) {
                                text.setAttribute('fill', item.fill);
                            }
                            text.textContent = item.text;
                            group.appendChild(text);
                        } else if (item.type === 'rect') {
                            const rect = document.createElementNS(SVG_NS, 'rect');
                            rect.setAttribute('x', item.x);
                            rect.setAttribute('y', item.y);
                            rect.setAttribute('width', item.width);
                            rect.setAttribute('height', item.height);
                            rect.setAttribute('rx', item.rx);
                            rect.setAttribute('fill', item.fill);
                            rect.setAttribute('stroke', item.stroke);
                            rect.setAttribute('stroke-width', item.strokeWidth);
                            if (item.strokeDasharray) {
                                rect.setAttribute('stroke-dasharray', item.strokeDasharray);
                            }
                            group.appendChild(rect);
                        }
                    });
                }

                interactiveDiagram.appendChild(group);
            }

            // 연결선 생성
            diagramConnectors.forEach((connector, index) => {
                const group = document.createElementNS(SVG_NS, 'g');
                group.classList.add('diagram-connector');
                group.setAttribute('data-from', connector.from);
                group.setAttribute('data-to', connector.to);

                const path = document.createElementNS(SVG_NS, 'path');
                path.setAttribute('d', connector.path);
                path.setAttribute('stroke', connector.stroke);
                path.setAttribute('stroke-width', connector.strokeWidth);
                path.setAttribute('fill', connector.fill);
                if (connector.strokeDasharray) {
                    path.setAttribute('stroke-dasharray', connector.strokeDasharray);
                }

                group.appendChild(path);
                interactiveDiagram.appendChild(group);
            });
        }

        // 다이어그램 요소 생성
        createDiagramElements();

        // 모든 다이어그램 요소에 대해 초기 위치 저장
        document.querySelectorAll('.diagram-element').forEach(element => {
            const id = element.getAttribute('data-element-id');
            if (id) {
                // 요소의 초기 위치 저장
                initialPositions[id] = { element, x: 0, y: 0 };

                // 요소에 커서 스타일 적용
                element.style.cursor = 'grab';

                // 요소에 마우스 이벤트 리스너 추가
                element.addEventListener('mousedown', startDrag);
            }
        });

        // 연결선 정보 수집
        document.querySelectorAll('.diagram-connector').forEach(connector => {
            const fromId = connector.getAttribute('data-from');
            const toId = connector.getAttribute('data-to');

            if (fromId && toId) {
                if (!connections[fromId]) connections[fromId] = [];
                if (!connections[toId]) connections[toId] = [];

                connections[fromId].push({ connector, isFrom: true, targetId: toId });
                connections[toId].push({ connector, isFrom: false, targetId: fromId });
            }
        });

        // 드래그 시작 함수
        function startDrag(event) {
            event.preventDefault();

            // 현재 클릭된 요소 (가장 가까운 diagram-element 찾기)
            selectedElement = event.target.closest('.diagram-element');
            if (!selectedElement) return;

            const id = selectedElement.getAttribute('data-element-id');
            if (!id) return;

            // 드래그 중인 요소 스타일 변경
            selectedElement.style.cursor = 'grabbing';
            selectedElement.classList.add('dragging');

            // 현재 요소의 위치 정보
            const position = initialPositions[id];

            // 마우스 위치와 요소 위치의 차이 계산
            offset = {
                x: event.clientX - position.x,
                y: event.clientY - position.y
            };

            // 전역 이벤트 리스너 추가
            document.addEventListener('mousemove', drag);
            document.addEventListener('mouseup', endDrag);
        }

        // 드래그 중 함수
        function drag(event) {
            if (!selectedElement) return;

            event.preventDefault();

            const id = selectedElement.getAttribute('data-element-id');
            if (!id) return;

            // 새 위치 계산
            const newX = event.clientX - offset.x;
            const newY = event.clientY - offset.y;

            // 위치 업데이트
            initialPositions[id].x = newX;
            initialPositions[id].y = newY;

            // 요소에 변환 적용
            selectedElement.setAttribute('transform', `translate(${newX}, ${newY})`);

            // 연결된 선 업데이트
            updateConnections(id);
        }

        // 드래그 종료 함수
        function endDrag() {
            if (!selectedElement) return;

            // 스타일 복원
            selectedElement.style.cursor = 'grab';
            selectedElement.classList.remove('dragging');

            // 전역 이벤트 리스너 제거
            document.removeEventListener('mousemove', drag);
            document.removeEventListener('mouseup', endDrag);

            selectedElement = null;
        }

        // 요소의 중심 좌표와 크기 계산 함수
        function getElementBounds(element) {
            // 요소 내의 rect 요소 찾기
            const rect = element.querySelector('rect');
            if (!rect) return null;

            // rect의 속성 가져오기
            const x = parseFloat(rect.getAttribute('x'));
            const y = parseFloat(rect.getAttribute('y'));
            const width = parseFloat(rect.getAttribute('width'));
            const height = parseFloat(rect.getAttribute('height'));
            const rx = parseFloat(rect.getAttribute('rx') || 0);

            // 요소의 현재 위치 가져오기
            const id = element.getAttribute('data-element-id');
            const position = initialPositions[id] || { x: 0, y: 0 };

            // 중심 좌표 계산
            const centerX = x + width / 2 + position.x;
            const centerY = y + height / 2 + position.y;

            return {
                x, y, width, height, rx,
                centerX, centerY,
                left: x + position.x,
                top: y + position.y,
                right: x + width + position.x,
                bottom: y + height + position.y
            };
        }

        // 두 요소 사이의 연결점 계산 함수
        function calculateConnectionPoints(sourceElement, targetElement) {
            const sourceBounds = getElementBounds(sourceElement);
            const targetBounds = getElementBounds(targetElement);

            if (!sourceBounds || !targetBounds) return null;

            // 두 요소의 중심점 사이의 방향 벡터 계산
            const dx = targetBounds.centerX - sourceBounds.centerX;
            const dy = targetBounds.centerY - sourceBounds.centerY;

            // 방향 벡터 정규화
            const length = Math.sqrt(dx * dx + dy * dy);
            const nx = dx / length;
            const ny = dy / length;

            // 소스 요소의 가장자리 교차점 계산
            let sourceX, sourceY;

            // 수평 방향이 더 강한 경우
            if (Math.abs(nx) > Math.abs(ny)) {
                if (nx > 0) {
                    // 오른쪽 방향
                    sourceX = sourceBounds.right;
                    sourceY = sourceBounds.centerY;
                } else {
                    // 왼쪽 방향
                    sourceX = sourceBounds.left;
                    sourceY = sourceBounds.centerY;
                }
            } else {
                if (ny > 0) {
                    // 아래쪽 방향
                    sourceX = sourceBounds.centerX;
                    sourceY = sourceBounds.bottom;
                } else {
                    // 위쪽 방향
                    sourceX = sourceBounds.centerX;
                    sourceY = sourceBounds.top;
                }
            }

            // 타겟 요소의 가장자리 교차점 계산
            let targetX, targetY;

            // 수평 방향이 더 강한 경우
            if (Math.abs(nx) > Math.abs(ny)) {
                if (nx > 0) {
                    // 오른쪽 방향
                    targetX = targetBounds.left;
                    targetY = targetBounds.centerY;
                } else {
                    // 왼쪽 방향
                    targetX = targetBounds.right;
                    targetY = targetBounds.centerY;
                }
            } else {
                if (ny > 0) {
                    // 아래쪽 방향
                    targetX = targetBounds.centerX;
                    targetY = targetBounds.top;
                } else {
                    // 위쪽 방향
                    targetX = targetBounds.centerX;
                    targetY = targetBounds.bottom;
                }
            }

            return {
                sourceX, sourceY,
                targetX, targetY
            };
        }

        // 베지어 곡선 경로 생성 함수
        function createBezierPath(sourceX, sourceY, targetX, targetY) {
            // 방향 벡터 계산
            const dx = targetX - sourceX;
            const dy = targetY - sourceY;

            // 방향 벡터 정규화
            const length = Math.sqrt(dx * dx + dy * dy);
            const nx = dx / length;
            const ny = dy / length;

            // 수직 벡터 계산 (방향 벡터에 수직인 벡터)
            const perpX = -ny;
            const perpY = nx;

            // 두 점 사이의 각도 계산 (라디안)
            const angle = Math.atan2(dy, dx);

            // 곡률 계수 계산 (거리와 각도에 따라 동적으로 조정)
            const curvature = adjustCurvature(sourceX, sourceY, targetX, targetY, angle);

            // 제어점 거리 계산 (거리에 비례하여 조정)
            const controlDistance = Math.min(length * 0.3, 60);

            // 제어점의 수직 오프셋 계산 (자연스러운 곡선을 위해)
            // 각도에 따라 오프셋 조정 (0도 또는 90도에 가까울수록 오프셋 감소)
            const angleOffset = Math.sin(2 * angle) * 0.5 + 0.5; // 0~1 사이 값
            const perpOffset = Math.min(length * 0.2, 40) * angleOffset;

            // 제어점 계산 - 항상 방향 벡터와 수직 벡터를 모두 고려
            let control1X, control1Y, control2X, control2Y;

            // 첫 번째 제어점: 시작점에서 방향 벡터를 따라 이동 + 수직 방향 오프셋
            control1X = sourceX + nx * controlDistance + perpX * perpOffset;
            control1Y = sourceY + ny * controlDistance + perpY * perpOffset;

            // 두 번째 제어점: 끝점에서 반대 방향 벡터를 따라 이동 + 수직 방향 오프셋
            control2X = targetX - nx * controlDistance + perpX * perpOffset;
            control2Y = targetY - ny * controlDistance + perpY * perpOffset;

            // 특수 케이스 처리: 거의 수직 또는 수평인 경우
            const isNearlyHorizontal = Math.abs(ny) < 0.1;
            const isNearlyVertical = Math.abs(nx) < 0.1;

            if (isNearlyHorizontal) {
                // 거의 수평인 경우, 수직 오프셋 증가
                const vertOffset = Math.min(length * 0.15, 30);
                control1Y = sourceY + vertOffset;
                control2Y = targetY + vertOffset;
            } else if (isNearlyVertical) {
                // 거의 수직인 경우, 수평 오프셋 증가
                const horizOffset = Math.min(length * 0.15, 30);
                control1X = sourceX + horizOffset;
                control2X = targetX + horizOffset;
            }

            // 두 요소가 매우 가까운 경우 (짧은 연결선)
            if (length < 100) {
                // 중간점 계산
                const midX = (sourceX + targetX) / 2;
                const midY = (sourceY + targetY) / 2;

                // 중간점에서 수직 방향으로 이동한 제어점 계산
                const shortOffset = Math.max(length * 0.3, 20);

                // 제어점을 중간점 주변에 배치
                control1X = midX + perpX * shortOffset * 0.7;
                control1Y = midY + perpY * shortOffset * 0.7;
                control2X = midX + perpX * shortOffset * 0.7;
                control2Y = midY + perpY * shortOffset * 0.7;
            }

            // 두 요소가 대각선 방향으로 멀리 떨어져 있는 경우 곡선을 더 부드럽게 조정
            if (Math.abs(dx) > 150 && Math.abs(dy) > 150) {
                // 중간점 계산
                const midX = (sourceX + targetX) / 2;
                const midY = (sourceY + targetY) / 2;

                // 중간점에서 수직 방향으로 이동한 제어점 계산
                const longOffset = Math.min(length * 0.25, 50);

                // 제어점 위치 조정 - 중간점에서 약간 떨어진 위치에 배치
                control1X = midX - nx * longOffset * 0.5 + perpX * longOffset;
                control1Y = midY - ny * longOffset * 0.5 + perpY * longOffset;
                control2X = midX + nx * longOffset * 0.5 + perpX * longOffset;
                control2Y = midY + ny * longOffset * 0.5 + perpY * longOffset;
            }

            // 3차 베지어 곡선 사용 (제어점 2개)
            return `M${sourceX},${sourceY} C${control1X},${control1Y} ${control2X},${control2Y} ${targetX},${targetY}`;
        }

        // 연결선 곡률 조정 함수
        function adjustCurvature(sourceX, sourceY, targetX, targetY, angle) {
            // 두 점 사이의 거리 계산
            const dx = Math.abs(targetX - sourceX);
            const dy = Math.abs(targetY - sourceY);
            const distance = Math.sqrt(dx * dx + dy * dy);

            // 기본 곡률 계산 (거리에 따라 조정)
            let baseCurvature = Math.min(0.35, Math.max(0.15, distance / 600));

            // 각도에 따른 곡률 조정 (0도 또는 90도에 가까울수록 곡률 증가)
            const angleNormalized = Math.abs(angle) % (Math.PI / 2);
            const angleEffect = Math.min(1, Math.abs(angleNormalized - Math.PI / 4) / (Math.PI / 4));
            baseCurvature *= (1 + angleEffect * 0.3);

            // 거리에 따른 추가 조정
            if (distance < 100) {
                // 짧은 거리는 곡률 증가
                baseCurvature *= 1.4;
            } else if (distance > 300) {
                // 긴 거리는 곡률 약간 감소
                baseCurvature *= 0.9;
            }

            // 수직/수평 방향에 따른 곡률 조정
            if (dx < 50 || dy < 50) {
                // 거의 수직이나 수평인 경우 곡률 증가
                baseCurvature *= 1.5;
            } else if (Math.abs(dx - dy) < 50) {
                // 대각선 방향인 경우 곡률 약간 증가
                baseCurvature *= 1.2;
            }

            return baseCurvature;
        }

        // 페이지 로드 시 초기 연결선 설정
        function initializeConnections() {
            document.querySelectorAll('.diagram-connector').forEach(connector => {
                const fromId = connector.getAttribute('data-from');
                const toId = connector.getAttribute('data-to');

                if (!fromId || !toId) return;

                const sourceElement = document.querySelector(`.diagram-element[data-element-id="${fromId}"]`);
                const targetElement = document.querySelector(`.diagram-element[data-element-id="${toId}"]`);

                if (!sourceElement || !targetElement) return;

                // 연결점 계산
                const connectionPoints = calculateConnectionPoints(sourceElement, targetElement);
                if (!connectionPoints) return;

                // 베지어 곡선 경로 생성
                const path = connector.querySelector('path');
                if (path) {
                    const pathData = createBezierPath(
                        connectionPoints.sourceX,
                        connectionPoints.sourceY,
                        connectionPoints.targetX,
                        connectionPoints.targetY
                    );
                    path.setAttribute('d', pathData);
                }

                // 폴리곤 요소는 제거됨 (화살표 대신 연결선만 사용)
            });
        }

        // 연결선 업데이트 함수
        function updateConnections(id) {
            if (!connections[id]) return;

            connections[id].forEach(connection => {
                const { connector, isFrom, targetId } = connection;

                // 현재 요소와 타겟 요소
                const sourceElement = document.querySelector(`.diagram-element[data-element-id="${id}"]`);
                const targetElement = document.querySelector(`.diagram-element[data-element-id="${targetId}"]`);

                if (!sourceElement || !targetElement) return;

                // 연결점 계산
                const connectionPoints = isFrom
                    ? calculateConnectionPoints(sourceElement, targetElement)
                    : calculateConnectionPoints(targetElement, sourceElement);

                if (!connectionPoints) return;

                // 베지어 곡선 경로 업데이트
                const path = connector.querySelector('path');
                if (path) {
                    let pathData;
                    if (isFrom) {
                        pathData = createBezierPath(
                            connectionPoints.sourceX,
                            connectionPoints.sourceY,
                            connectionPoints.targetX,
                            connectionPoints.targetY
                        );
                    } else {
                        pathData = createBezierPath(
                            connectionPoints.targetX,
                            connectionPoints.targetY,
                            connectionPoints.sourceX,
                            connectionPoints.sourceY
                        );
                    }
                    path.setAttribute('d', pathData);
                }

                // 폴리곤 요소는 제거됨 (화살표 대신 연결선만 사용)
            });

            // 모든 연결선 업데이트 (양쪽 끝점이 모두 이동한 경우 처리)
            document.querySelectorAll('.diagram-connector').forEach(connector => {
                const fromId = connector.getAttribute('data-from');
                const toId = connector.getAttribute('data-to');

                if (fromId && toId && fromId !== id && toId !== id) {
                    // 양쪽 요소 모두 이미 처리된 경우는 건너뜀
                    if (connections[fromId] && connections[fromId].some(c => c.targetId === toId)) {
                        return;
                    }

                    // 소스와 타겟 요소
                    const sourceElement = document.querySelector(`.diagram-element[data-element-id="${fromId}"]`);
                    const targetElement = document.querySelector(`.diagram-element[data-element-id="${toId}"]`);

                    if (!sourceElement || !targetElement) return;

                    // 연결점 계산
                    const connectionPoints = calculateConnectionPoints(sourceElement, targetElement);
                    if (!connectionPoints) return;

                    // 베지어 곡선 경로 업데이트
                    const path = connector.querySelector('path');
                    if (path) {
                        const pathData = createBezierPath(
                            connectionPoints.sourceX,
                            connectionPoints.sourceY,
                            connectionPoints.targetX,
                            connectionPoints.targetY
                        );
                        path.setAttribute('d', pathData);
                    }

                    // 폴리곤 요소는 제거됨 (화살표 대신 연결선만 사용)
                }
            });
        }

        // 페이지 로드 시 초기 연결선 설정
        initializeConnections();

        // 사용자에게 드래그 가능함을 알리는 툴팁 추가
        const tooltip = document.createElement('div');
        tooltip.textContent = '박스를 드래그하여 이동할 수 있습니다';
        tooltip.style.position = 'absolute';
        tooltip.style.top = '10px';
        tooltip.style.left = '50%';
        tooltip.style.transform = 'translateX(-50%)';
        tooltip.style.backgroundColor = 'rgba(0, 123, 255, 0.8)';
        tooltip.style.color = 'white';
        tooltip.style.padding = '5px 10px';
        tooltip.style.borderRadius = '4px';
        tooltip.style.fontSize = '14px';
        tooltip.style.zIndex = '1000';
        tooltip.style.opacity = '0';
        tooltip.style.transition = 'opacity 0.3s ease';

        document.querySelector('.architecture-diagram').appendChild(tooltip);

        // 툴팁 표시
        setTimeout(() => {
            tooltip.style.opacity = '1';

            // 3초 후 툴팁 숨기기
            setTimeout(() => {
                tooltip.style.opacity = '0';

                // 페이드 아웃 후 제거
                setTimeout(() => {
                    tooltip.remove();
                }, 300);
            }, 3000);
        }, 500);
    }

    // Close mobile menu when clicking outside
    document.addEventListener('click', function(event) {
        const isClickInsideNav = navLinks.contains(event.target);
        const isClickOnHamburger = hamburger.contains(event.target);

        if (!isClickInsideNav && !isClickOnHamburger && navLinks.classList.contains('active')) {
            navLinks.classList.remove('active');
        }
    });

    // Copy buttons functionality
    const copyButtons = document.querySelectorAll('.copy-btn');

    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const textToCopy = this.getAttribute('data-clipboard-text');

            // Create a temporary textarea element
            const textarea = document.createElement('textarea');
            textarea.value = textToCopy;
            textarea.setAttribute('readonly', '');
            textarea.style.position = 'absolute';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);

            // Select and copy the text
            textarea.select();
            document.execCommand('copy');

            // Remove the textarea
            document.body.removeChild(textarea);

            // Change button text temporarily
            const originalText = this.textContent;
            this.textContent = 'Copied!';

            // Restore original button text after a delay
            setTimeout(() => {
                this.textContent = originalText;
            }, 2000);
        });
    });

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();

            // Skip if it's a link with empty href or just "#"
            if (this.getAttribute('href') === '#' || this.getAttribute('href') === '') {
                return;
            }

            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);

            if (targetElement) {
                // Close mobile menu if open
                if (navLinks.classList.contains('active')) {
                    navLinks.classList.remove('active');
                }

                // Scroll to the target element
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Highlight active section in navigation
    const sections = document.querySelectorAll('section[id]');
    const navItems = document.querySelectorAll('.nav-links a[href^="#"]');

    function highlightActiveSection() {
        const scrollPosition = window.scrollY;

        sections.forEach(section => {
            const sectionTop = section.offsetTop - 100;
            const sectionHeight = section.offsetHeight;
            const sectionId = section.getAttribute('id');

            if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                navItems.forEach(navItem => {
                    navItem.classList.remove('active');
                    if (navItem.getAttribute('href') === '#' + sectionId) {
                        navItem.classList.add('active');
                    }
                });
            }
        });
    }

    window.addEventListener('scroll', highlightActiveSection);
    highlightActiveSection(); // Highlight active section on page load
});
