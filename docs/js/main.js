document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle
    const hamburger = document.querySelector('.hamburger');
    const navLinks = document.querySelector('.nav-links');

    if (hamburger) {
        hamburger.addEventListener('click', function() {
            navLinks.classList.toggle('active');
        });
    }

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

            // 제어점 거리 계산 (거리에 비례하여 조정)
            const distance = Math.min(length * 0.4, 50);

            // 수직 벡터 계산 (방향 벡터에 수직인 벡터)
            const perpX = -ny;
            const perpY = nx;

            // 제어점 계산 (항상 외부로 휘어지도록)
            // 두 요소 사이의 중간점
            const midX = (sourceX + targetX) / 2;
            const midY = (sourceY + targetY) / 2;

            // 중간점에서 수직 방향으로 이동한 제어점
            const controlX = midX + perpX * distance;
            const controlY = midY + perpY * distance;

            // 2차 베지어 곡선 사용 (제어점 1개)
            return `M${sourceX},${sourceY} Q${controlX},${controlY} ${targetX},${targetY}`;
        }

        // 연결선 곡률 조정 함수
        function adjustCurvature(sourceX, sourceY, targetX, targetY) {
            // 두 점 사이의 거리 계산
            const dx = Math.abs(targetX - sourceX);
            const dy = Math.abs(targetY - sourceY);
            const distance = Math.sqrt(dx * dx + dy * dy);

            // 거리에 따라 곡률 조정 (거리가 멀수록 곡률 증가)
            return Math.min(0.4, Math.max(0.2, distance / 500));
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
