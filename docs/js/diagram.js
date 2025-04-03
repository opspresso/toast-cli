// Architecture diagram functionality
document.addEventListener('DOMContentLoaded', function() {
    // Architecture diagram drag functionality
    const interactiveDiagram = document.querySelector('.interactive-diagram');
    if (interactiveDiagram) {
        // 설정 변수
        const DEFAULT_OPACITY = 0.4;       // 기본 연결선 투명도
        const DRAG_OPACITY = 0.5;          // 드래그 중인 요소의 연결선 투명도
        const POINT_SCALE_FACTOR = 1.5;    // 드래그 중인 요소의 연결점 크기 확대 비율

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

                // 스타일 속성 설정
                path.setAttribute('stroke', connector.stroke);
                path.setAttribute('stroke-width', connector.strokeWidth);
                path.setAttribute('fill', connector.fill);
                path.setAttribute('opacity', DEFAULT_OPACITY.toString()); // 기본 투명도 설정
                if (connector.strokeDasharray) {
                    path.setAttribute('stroke-dasharray', connector.strokeDasharray);
                }

                // 시작점과 끝점에 원 추가
                const startCircle = document.createElementNS(SVG_NS, 'circle');
                startCircle.classList.add('connector-point', 'start-point');
                startCircle.setAttribute('r', connector.strokeWidth); // 기본 크기는 선 두께와 동일
                startCircle.setAttribute('fill', connector.stroke);
                startCircle.setAttribute('data-original-r', connector.strokeWidth); // 원래 크기 저장

                const endCircle = document.createElementNS(SVG_NS, 'circle');
                endCircle.classList.add('connector-point', 'end-point');
                endCircle.setAttribute('r', connector.strokeWidth); // 기본 크기는 선 두께와 동일
                endCircle.setAttribute('fill', connector.stroke);
                endCircle.setAttribute('data-original-r', connector.strokeWidth); // 원래 크기 저장

                group.appendChild(path);
                group.appendChild(startCircle);
                group.appendChild(endCircle);
                interactiveDiagram.appendChild(group);
            });

            // 모든 연결선 초기화
            initializeAllConnections();
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

            // 요소를 맨 앞으로 가져오기 (SVG에서는 나중에 추가된 요소가 앞에 표시됨)
            // 부모 노드에서 요소를 제거한 후 다시 추가
            const parent = selectedElement.parentNode;
            parent.removeChild(selectedElement);
            parent.appendChild(selectedElement);

            // 연결된 모든 연결선도 맨 앞으로 가져오기
            if (id && connections[id]) {
                connections[id].forEach(connection => {
                    const { connector } = connection;
                    // 연결선을 부모 노드에서 제거한 후 다시 추가
                    const connectorParent = connector.parentNode;
                    connectorParent.removeChild(connector);
                    connectorParent.appendChild(connector);
                });
            }

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

            // 이동 중인 요소와 연결된 모든 연결선의 점 크기 확대 및 연결선을 맨 앞으로 가져오기
            if (connections[id]) {
                connections[id].forEach(connection => {
                    const { connector, isFrom } = connection;

                    // 이동 중인 요소와 연결된 점 찾기
                    const pointSelector = isFrom ? '.start-point' : '.end-point';
                    const point = connector.querySelector(pointSelector);

                    if (point) {
                        const originalR = parseFloat(point.getAttribute('data-original-r'));
                        point.setAttribute('r', (originalR * POINT_SCALE_FACTOR).toString()); // 원래 크기의 확대 비율로 설정
                    }

                    // 드래그 중인 요소와 연결된 연결선의 투명도 변경
                    const path = connector.querySelector('path');
                    if (path) {
                        path.setAttribute('opacity', DRAG_OPACITY.toString()); // 드래그 중인 요소의 연결선 투명도 설정
                    }

                    // 연결선을 맨 앞으로 가져오기 (드래그 중에도 계속 맨 앞에 표시)
                    const connectorParent = connector.parentNode;
                    connectorParent.removeChild(connector);
                    connectorParent.appendChild(connector);
                });
            }

            // 요소를 맨 앞으로 가져오기 (연결선 위에 표시)
            const parent = selectedElement.parentNode;
            parent.removeChild(selectedElement);
            parent.appendChild(selectedElement);
        }

        // 드래그 종료 함수
        function endDrag() {
            if (!selectedElement) return;

            const id = selectedElement.getAttribute('data-element-id');
            if (id && connections[id]) {
                // 모든 연결된 점의 크기를 원래대로 복원하고 투명도 복원
                connections[id].forEach(connection => {
                    const { connector } = connection;

                    // 모든 점 찾기
                    const points = connector.querySelectorAll('.connector-point');

                    points.forEach(point => {
                        const originalR = parseFloat(point.getAttribute('data-original-r'));
                        point.setAttribute('r', originalR); // 원래 크기로 복원
                    });

                    // 연결선 투명도를 기본값(0.6)으로 복원
                    const path = connector.querySelector('path');
                    if (path) {
                        path.setAttribute('opacity', DEFAULT_OPACITY.toString()); // 기본 투명도로 복원
                    }
                });
            }

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

        // 두 요소 사이의 연결점 계산 함수 - 개선된 가중치 기반 연결점 선택
        function calculateConnectionPoints(sourceElement, targetElement) {
            const sourceBounds = getElementBounds(sourceElement);
            const targetBounds = getElementBounds(targetElement);

            if (!sourceBounds || !targetBounds) return null;

            // 두 요소의 상대적 위치 관계 분석
            const sourceCenter = {
                x: sourceBounds.centerX,
                y: sourceBounds.centerY
            };
            const targetCenter = {
                x: targetBounds.centerX,
                y: targetBounds.centerY
            };

            // 방향 벡터 계산
            const dx = targetCenter.x - sourceCenter.x;
            const dy = targetCenter.y - sourceCenter.y;

            // 두 요소 사이의 주요 방향 결정 (수평/수직)
            const isHorizontalDominant = Math.abs(dx) > Math.abs(dy);

            // 소스 요소의 좌우상하 연결점
            const sourcePoints = [
                // 위쪽 중앙
                {
                    x: sourceBounds.left + sourceBounds.width / 2,
                    y: sourceBounds.top,
                    direction: 'top',
                    // 위쪽 방향이 적합한 경우 (타겟이 위에 있을 때)
                    directionFitness: dy < 0 ? 1 : 0
                },
                // 오른쪽 중앙
                {
                    x: sourceBounds.right,
                    y: sourceBounds.top + sourceBounds.height / 2,
                    direction: 'right',
                    // 오른쪽 방향이 적합한 경우 (타겟이 오른쪽에 있을 때)
                    directionFitness: dx > 0 ? 1 : 0
                },
                // 아래쪽 중앙
                {
                    x: sourceBounds.left + sourceBounds.width / 2,
                    y: sourceBounds.bottom,
                    direction: 'bottom',
                    // 아래쪽 방향이 적합한 경우 (타겟이 아래에 있을 때)
                    directionFitness: dy > 0 ? 1 : 0
                },
                // 왼쪽 중앙
                {
                    x: sourceBounds.left,
                    y: sourceBounds.top + sourceBounds.height / 2,
                    direction: 'left',
                    // 왼쪽 방향이 적합한 경우 (타겟이 왼쪽에 있을 때)
                    directionFitness: dx < 0 ? 1 : 0
                }
            ];

            // 타겟 요소의 좌우상하 연결점
            const targetPoints = [
                // 위쪽 중앙
                {
                    x: targetBounds.left + targetBounds.width / 2,
                    y: targetBounds.top,
                    direction: 'top',
                    // 위쪽 방향이 적합한 경우 (소스가 위에 있을 때)
                    directionFitness: dy > 0 ? 1 : 0
                },
                // 오른쪽 중앙
                {
                    x: targetBounds.right,
                    y: targetBounds.top + targetBounds.height / 2,
                    direction: 'right',
                    // 오른쪽 방향이 적합한 경우 (소스가 오른쪽에 있을 때)
                    directionFitness: dx < 0 ? 1 : 0
                },
                // 아래쪽 중앙
                {
                    x: targetBounds.left + targetBounds.width / 2,
                    y: targetBounds.bottom,
                    direction: 'bottom',
                    // 아래쪽 방향이 적합한 경우 (소스가 아래에 있을 때)
                    directionFitness: dy < 0 ? 1 : 0
                },
                // 왼쪽 중앙
                {
                    x: targetBounds.left,
                    y: targetBounds.top + targetBounds.height / 2,
                    direction: 'left',
                    // 왼쪽 방향이 적합한 경우 (소스가 왼쪽에 있을 때)
                    directionFitness: dx > 0 ? 1 : 0
                }
            ];

            // 가중치 기반 최적 연결점 찾기
            let maxScore = -Infinity;
            let bestSourcePoint = null;
            let bestTargetPoint = null;

            // 모든 가능한 점 쌍에 대해 가중치 계산
            for (const sourcePoint of sourcePoints) {
                for (const targetPoint of targetPoints) {
                    // 1. 거리 계산 (가까울수록 점수 높음)
                    const connDx = targetPoint.x - sourcePoint.x;
                    const connDy = targetPoint.y - sourcePoint.y;
                    const distance = Math.sqrt(connDx * connDx + connDy * connDy);

                    // 거리에 따른 기본 점수 (거리가 가까울수록 높은 점수)
                    // 최대 거리를 1000으로 가정하고 정규화
                    const maxDistance = 1000;
                    const distanceScore = 1 - Math.min(distance, maxDistance) / maxDistance;

                    // 2. 방향 적합성 점수 (요소의 상대적 위치에 맞는 방향일수록 높은 점수)
                    const directionFitnessScore = (sourcePoint.directionFitness + targetPoint.directionFitness) * 0.5;

                    // 3. 자기 요소 가림 검사 (연결선이 소스나 타겟 요소 자체를 가로지르는지 확인)
                    let selfIntersectionPenalty = 0;

                    // 소스 요소 가림 검사 - 개선된 방식
                    // 연결점에서 시작하는 선이 요소를 가로지르는지 정확히 확인
                    if (doesLineIntersectElement(
                        sourcePoint.x, sourcePoint.y,
                        targetPoint.x, targetPoint.y,
                        sourceBounds,
                        sourcePoint.direction
                    )) {
                        // 요소를 가로지르는 경우 매우 큰 패널티 부여
                        selfIntersectionPenalty += 5.0;
                    }

                    // 타겟 요소 가림 검사 - 개선된 방식
                    if (doesLineIntersectElement(
                        targetPoint.x, targetPoint.y,
                        sourcePoint.x, sourcePoint.y,
                        targetBounds,
                        targetPoint.direction
                    )) {
                        selfIntersectionPenalty += 5.0;
                    }

                    // 4. 다른 요소 가림 검사
                    let otherIntersectionPenalty = 0;

                    // 다른 모든 요소와의 교차 검사
                    document.querySelectorAll('.diagram-element').forEach(element => {
                        if (element !== sourceElement && element !== targetElement) {
                            const bounds = getElementBounds(element);
                            if (bounds && lineIntersectsRectangle(
                                sourcePoint.x, sourcePoint.y,
                                targetPoint.x, targetPoint.y,
                                bounds.left, bounds.top,
                                bounds.right, bounds.bottom
                            )) {
                                otherIntersectionPenalty += 1.0;
                            }
                        }
                    });

                    // 5. 연결선 방향 자연스러움 점수
                    // 수평/수직 주요 방향과 일치하는 연결점 선호
                    let naturalDirectionScore = 0;

                    if (isHorizontalDominant) {
                        // 수평 방향이 주요 방향인 경우
                        if ((sourcePoint.direction === 'left' || sourcePoint.direction === 'right') &&
                            (targetPoint.direction === 'left' || targetPoint.direction === 'right')) {
                            naturalDirectionScore = 0.3;
                        }
                    } else {
                        // 수직 방향이 주요 방향인 경우
                        if ((sourcePoint.direction === 'top' || sourcePoint.direction === 'bottom') &&
                            (targetPoint.direction === 'top' || targetPoint.direction === 'bottom')) {
                            naturalDirectionScore = 0.3;
                        }
                    }

                    // 6. 반대 방향 연결점 보너스 (예: 소스의 '오른쪽'과 타겟의 '왼쪽')
                    let oppositeDirectionBonus = 0;
                    if (
                        (sourcePoint.direction === 'right' && targetPoint.direction === 'left') ||
                        (sourcePoint.direction === 'left' && targetPoint.direction === 'right') ||
                        (sourcePoint.direction === 'top' && targetPoint.direction === 'bottom') ||
                        (sourcePoint.direction === 'bottom' && targetPoint.direction === 'top')
                    ) {
                        oppositeDirectionBonus = 0.3;
                    }

                    // 7. 요소 중심 방향 일치 보너스
                    // 요소 중심에서 연결점으로의 방향과 연결선의 방향이 일치할 때 보너스
                    let centerAlignmentBonus = 0;

                    // 소스 요소 중심에서 연결점 방향 확인
                    const sourceCenterToPointDx = sourcePoint.x - sourceCenter.x;
                    const sourceCenterToPointDy = sourcePoint.y - sourceCenter.y;

                    // 연결선 방향 확인
                    const lineDirectionDx = targetPoint.x - sourcePoint.x;
                    const lineDirectionDy = targetPoint.y - sourcePoint.y;

                    // 두 방향의 내적으로 방향 일치 확인 (양수면 같은 방향)
                    const sourceDotProduct = sourceCenterToPointDx * lineDirectionDx + sourceCenterToPointDy * lineDirectionDy;

                    if (sourceDotProduct > 0) {
                        centerAlignmentBonus += 0.2;
                    }

                    // 타겟 요소에 대해서도 동일하게 확인
                    const targetCenterToPointDx = targetPoint.x - targetCenter.x;
                    const targetCenterToPointDy = targetPoint.y - targetCenter.y;

                    const targetLineDirectionDx = sourcePoint.x - targetPoint.x;
                    const targetLineDirectionDy = sourcePoint.y - targetPoint.y;

                    const targetDotProduct = targetCenterToPointDx * targetLineDirectionDx + targetCenterToPointDy * targetLineDirectionDy;

                    if (targetDotProduct > 0) {
                        centerAlignmentBonus += 0.2;
                    }

                    // 최종 점수 계산
                    // 거리 점수가 가장 중요하고, 방향 적합성, 자연스러움, 반대 방향 보너스를 더하고, 교차 패널티 적용
                    const totalScore =
                        distanceScore * 0.4 +
                        directionFitnessScore * 0.3 +
                        naturalDirectionScore +
                        oppositeDirectionBonus +
                        centerAlignmentBonus -
                        selfIntersectionPenalty -
                        otherIntersectionPenalty * 0.5;

                    if (totalScore > maxScore) {
                        maxScore = totalScore;
                        bestSourcePoint = sourcePoint;
                        bestTargetPoint = targetPoint;
                    }
                }
            }

            // 최적 연결점과 방향 정보 반환
            return {
                sourceX: bestSourcePoint.x,
                sourceY: bestSourcePoint.y,
                targetX: bestTargetPoint.x,
                targetY: bestTargetPoint.y,
                sourceDirection: bestSourcePoint.direction,
                targetDirection: bestTargetPoint.direction
            };
        }

        // 선이 요소를 가로지르는지 확인하는 개선된 함수
        function doesLineIntersectElement(x1, y1, x2, y2, bounds, startDirection) {
            // 연결점 방향에 따라 요소 내부에서 시작하는 부분은 교차로 간주하지 않음
            let adjustedX1 = x1;
            let adjustedY1 = y1;

            // 연결점 방향에 따라 시작점 약간 조정 (요소 바깥으로)
            const OFFSET = 0.1; // 아주 작은 오프셋

            switch (startDirection) {
                case 'top':
                    adjustedY1 = bounds.top - OFFSET;
                    break;
                case 'right':
                    adjustedX1 = bounds.right + OFFSET;
                    break;
                case 'bottom':
                    adjustedY1 = bounds.bottom + OFFSET;
                    break;
                case 'left':
                    adjustedX1 = bounds.left - OFFSET;
                    break;
            }

            // 조정된 시작점으로 교차 검사
            return lineIntersectsRectangle(
                adjustedX1, adjustedY1,
                x2, y2,
                bounds.left, bounds.top,
                bounds.right, bounds.bottom
            );
        }

        // 선분과 사각형의 교차 여부 확인 함수
        function lineIntersectsRectangle(x1, y1, x2, y2, rectLeft, rectTop, rectRight, rectBottom) {
            // 선분이 사각형의 네 변과 교차하는지 확인
            return (
                lineIntersectsLine(x1, y1, x2, y2, rectLeft, rectTop, rectRight, rectTop) || // 위쪽 변
                lineIntersectsLine(x1, y1, x2, y2, rectRight, rectTop, rectRight, rectBottom) || // 오른쪽 변
                lineIntersectsLine(x1, y1, x2, y2, rectLeft, rectBottom, rectRight, rectBottom) || // 아래쪽 변
                lineIntersectsLine(x1, y1, x2, y2, rectLeft, rectTop, rectLeft, rectBottom) // 왼쪽 변
            );
        }

        // 두 선분의 교차 여부 확인 함수
        function lineIntersectsLine(x1, y1, x2, y2, x3, y3, x4, y4) {
            // 두 선분의 방향 벡터
            const dx1 = x2 - x1;
            const dy1 = y2 - y1;
            const dx2 = x4 - x3;
            const dy2 = y4 - y3;

            // 두 선분의 교차 여부 계산
            const denominator = dy2 * dx1 - dx2 * dy1;

            // 두 선분이 평행한 경우
            if (denominator === 0) {
                return false;
            }

            // 교차점의 매개변수 계산
            const ua = (dx2 * (y1 - y3) - dy2 * (x1 - x3)) / denominator;
            const ub = (dx1 * (y1 - y3) - dy1 * (x1 - x3)) / denominator;

            // 교차점이 두 선분 위에 있는지 확인
            return ua >= 0 && ua <= 1 && ub >= 0 && ub <= 1;
        }

        // 베지어 곡선 경로 생성 함수 - 개선된 자연스러운 곡선
        function createBezierPath(sourceX, sourceY, targetX, targetY, sourceDirection, targetDirection) {
            // 방향 벡터 계산
            const dx = targetX - sourceX;
            const dy = targetY - sourceY;

            // 거리 계산
            const distance = Math.sqrt(dx * dx + dy * dy);

            // 방향 결정 (수직/수평)
            const isHorizontal = Math.abs(dx) > Math.abs(dy);

            // 제어점 거리 계산 (거리에 비례하되 최소/최대값 설정)
            // 거리에 따라 동적으로 조정하여 더 자연스러운 곡선 생성
            const controlDistanceFactor = Math.min(0.4, Math.max(0.2, distance / 500));
            const controlDistance = distance * controlDistanceFactor;

            let controlX1, controlY1, controlX2, controlY2;

            // 연결점 방향에 따른 제어점 위치 조정
            // 소스와 타겟의 연결점 방향을 고려하여 더 자연스러운 곡선 생성
            if (sourceDirection && targetDirection) {
                // 소스 연결점 방향에 따른 첫 번째 제어점 위치 계산
                switch (sourceDirection) {
                    case 'top':
                        controlX1 = sourceX;
                        controlY1 = sourceY - controlDistance;
                        break;
                    case 'right':
                        controlX1 = sourceX + controlDistance;
                        controlY1 = sourceY;
                        break;
                    case 'bottom':
                        controlX1 = sourceX;
                        controlY1 = sourceY + controlDistance;
                        break;
                    case 'left':
                        controlX1 = sourceX - controlDistance;
                        controlY1 = sourceY;
                        break;
                }

                // 타겟 연결점 방향에 따른 두 번째 제어점 위치 계산
                switch (targetDirection) {
                    case 'top':
                        controlX2 = targetX;
                        controlY2 = targetY - controlDistance;
                        break;
                    case 'right':
                        controlX2 = targetX + controlDistance;
                        controlY2 = targetY;
                        break;
                    case 'bottom':
                        controlX2 = targetX;
                        controlY2 = targetY + controlDistance;
                        break;
                    case 'left':
                        controlX2 = targetX - controlDistance;
                        controlY2 = targetY;
                        break;
                }

                // 반대 방향 연결점인 경우 제어점 조정 (예: 소스의 '오른쪽'과 타겟의 '왼쪽')
                if (
                    (sourceDirection === 'right' && targetDirection === 'left') ||
                    (sourceDirection === 'left' && targetDirection === 'right') ||
                    (sourceDirection === 'top' && targetDirection === 'bottom') ||
                    (sourceDirection === 'bottom' && targetDirection === 'top')
                ) {
                    // 중간 지점 계산
                    const midX = (sourceX + targetX) / 2;
                    const midY = (sourceY + targetY) / 2;

                    // 제어점을 중간 지점 쪽으로 약간 당겨서 더 부드러운 곡선 생성
                    controlX1 = (controlX1 + midX) / 2;
                    controlY1 = (controlY1 + midY) / 2;
                    controlX2 = (controlX2 + midX) / 2;
                    controlY2 = (controlY2 + midY) / 2;
                }
            } else {
                // 연결점 방향 정보가 없는 경우 기존 방식으로 계산
                if (isHorizontal) {
                    // 수평 방향 연결인 경우
                    const offsetY = Math.min(Math.abs(dy) * 0.5, 50) * (dy >= 0 ? 1 : -1);

                    // 첫 번째 제어점: 출발점에서 수평으로 이동 후 수직 방향으로 약간 휘어짐
                    controlX1 = sourceX + controlDistance * (dx >= 0 ? 1 : -1);
                    controlY1 = sourceY + offsetY * 0.3;

                    // 두 번째 제어점: 도착점에서 수평으로 이동 후 수직 방향으로 약간 휘어짐
                    controlX2 = targetX - controlDistance * (dx >= 0 ? 1 : -1);
                    controlY2 = targetY + offsetY * 0.3;
                } else {
                    // 수직 방향 연결인 경우
                    const offsetX = Math.min(Math.abs(dx) * 0.5, 50) * (dx >= 0 ? 1 : -1);

                    // 첫 번째 제어점: 출발점에서 수직으로 이동 후 수평 방향으로 약간 휘어짐
                    controlX1 = sourceX + offsetX * 0.3;
                    controlY1 = sourceY + controlDistance * (dy >= 0 ? 1 : -1);

                    // 두 번째 제어점: 도착점에서 수직으로 이동 후 수평 방향으로 약간 휘어짐
                    controlX2 = targetX + offsetX * 0.3;
                    controlY2 = targetY - controlDistance * (dy >= 0 ? 1 : -1);
                }

                // 대각선 방향 연결인 경우 추가 조정
                if (Math.abs(dx) > 50 && Math.abs(dy) > 50) {
                    // 대각선 방향의 경우 더 부드러운 곡선을 위해 제어점 조정
                    const midX = (sourceX + targetX) / 2;
                    const midY = (sourceY + targetY) / 2;

                    // 중간 지점에서 약간 벗어난 위치로 제어점 조정
                    const offsetX = Math.min(Math.abs(dx) * 0.2, 40) * (dx >= 0 ? 1 : -1);
                    const offsetY = Math.min(Math.abs(dy) * 0.2, 40) * (dy >= 0 ? 1 : -1);

                    // 대각선 방향에 따라 제어점 위치 미세 조정
                    const diagonalFactor = Math.min(Math.abs(dx / dy), Math.abs(dy / dx));

                    controlX1 = midX - offsetX + offsetY * 0.5 * diagonalFactor;
                    controlY1 = midY - offsetY - offsetX * 0.5 * diagonalFactor;
                    controlX2 = midX + offsetX + offsetY * 0.5 * diagonalFactor;
                    controlY2 = midY + offsetY - offsetX * 0.5 * diagonalFactor;
                }
            }

            // 3차 베지어 곡선 사용
            return `M${sourceX},${sourceY} C${controlX1},${controlY1} ${controlX2},${controlY2} ${targetX},${targetY}`;
        }

        // 모든 연결선 초기화 함수
        function initializeAllConnections() {
            // 모든 연결선에 대해 경로 계산 및 설정
            document.querySelectorAll('.diagram-connector').forEach(connector => {
                const fromId = connector.getAttribute('data-from');
                const toId = connector.getAttribute('data-to');

                if (!fromId || !toId) return;

                // 소스 및 타겟 요소 찾기
                const sourceElement = document.querySelector(`.diagram-element[data-element-id="${fromId}"]`);
                const targetElement = document.querySelector(`.diagram-element[data-element-id="${toId}"]`);

                if (!sourceElement || !targetElement) return;

                // 연결점 계산
                const connectionPoints = calculateConnectionPoints(sourceElement, targetElement);
                if (!connectionPoints) return;

                // 베지어 곡선 경로 생성 - 연결점 방향 정보 전달
                const pathData = createBezierPath(
                    connectionPoints.sourceX,
                    connectionPoints.sourceY,
                    connectionPoints.targetX,
                    connectionPoints.targetY,
                    connectionPoints.sourceDirection,
                    connectionPoints.targetDirection
                );

                // 경로 설정
                const path = connector.querySelector('path');
                if (path) {
                    path.setAttribute('d', pathData);
                }

                // 시작점과 끝점 원 위치 설정
                const startCircle = connector.querySelector('.start-point');
                const endCircle = connector.querySelector('.end-point');

                if (startCircle) {
                    startCircle.setAttribute('cx', connectionPoints.sourceX);
                    startCircle.setAttribute('cy', connectionPoints.sourceY);
                }

                if (endCircle) {
                    endCircle.setAttribute('cx', connectionPoints.targetX);
                    endCircle.setAttribute('cy', connectionPoints.targetY);
                }
            });
        }

        // 연결선 업데이트 함수
        function updateConnections(id) {
            if (!connections[id]) return;

            connections[id].forEach(connection => {
                const { connector, isFrom, targetId } = connection;

                // 현재 요소와 타겟 요소
                const sourceElement = document.querySelector(`.diagram-element[data-element-id="${isFrom ? id : targetId}"]`);
                const targetElement = document.querySelector(`.diagram-element[data-element-id="${isFrom ? targetId : id}"]`);

                if (!sourceElement || !targetElement) return;

                // 연결점 계산
                const connectionPoints = calculateConnectionPoints(sourceElement, targetElement);
                if (!connectionPoints) return;

                // 베지어 곡선 경로 업데이트
                const path = connector.querySelector('path');
                if (path) {
                    // 스트로크 속성 가져오기
                    const stroke = path.getAttribute('stroke');
                    const strokeWidth = path.getAttribute('stroke-width');
                    const strokeDasharray = path.getAttribute('stroke-dasharray');

                    // 베지어 곡선 경로 생성 - 연결점 방향 정보 전달
                    const pathData = createBezierPath(
                        connectionPoints.sourceX,
                        connectionPoints.sourceY,
                        connectionPoints.targetX,
                        connectionPoints.targetY,
                        connectionPoints.sourceDirection,
                        connectionPoints.targetDirection
                    );

                    // 경로 업데이트
                    path.setAttribute('d', pathData);

                    // 선 스타일 유지
                    path.setAttribute('stroke', stroke);
                    path.setAttribute('stroke-width', strokeWidth);
                    if (strokeDasharray) {
                        path.setAttribute('stroke-dasharray', strokeDasharray);
                    }
                }

                // 시작점과 끝점 원 위치 업데이트
                const startCircle = connector.querySelector('.start-point');
                const endCircle = connector.querySelector('.end-point');

                if (startCircle) {
                    startCircle.setAttribute('cx', connectionPoints.sourceX);
                    startCircle.setAttribute('cy', connectionPoints.sourceY);
                }

                if (endCircle) {
                    endCircle.setAttribute('cx', connectionPoints.targetX);
                    endCircle.setAttribute('cy', connectionPoints.targetY);
                }
            });
        }
    }
});
