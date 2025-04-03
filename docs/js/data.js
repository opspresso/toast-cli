
// Architecture diagram elements and connectors
// 다이어그램 요소 정의
const diagramElements = {
  // 제목
  'title': {
    type: 'title',
    content: [
      { type: 'text', x: 500, y: 50, fontFamily: 'Arial', fontSize: 28, textAnchor: 'middle', fontWeight: 'bold', text: 'Toast-cli Architecture' },
      { type: 'text', x: 500, y: 90, fontFamily: 'Arial', fontSize: 18, textAnchor: 'middle', fill: '#6c757d', text: 'Plugin-based Design Pattern v3.1.0' }
    ]
  },
  // 메인 CLI 박스
  'main-cli': {
    type: 'box',
    rect: { x: 300, y: 130, width: 400, height: 100, rx: 10, fill: '#e9f5ff', stroke: '#007bff', strokeWidth: 2 },
    content: [
      { type: 'text', x: 500, y: 175, fontFamily: 'Arial', fontSize: 20, textAnchor: 'middle', text: 'Main CLI Application' },
      { type: 'text', x: 500, y: 205, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', fill: '#6c757d', text: '(toast/__init__.py)' }
    ]
  },
  // 헬퍼 유틸리티 박스
  'helpers': {
    type: 'box',
    rect: { x: 750, y: 130, width: 200, height: 100, rx: 10, fill: '#e9f5ff', stroke: '#007bff', strokeWidth: 2 },
    content: [
      { type: 'text', x: 850, y: 175, fontFamily: 'Arial', fontSize: 18, textAnchor: 'middle', text: 'Helper Utilities' },
      { type: 'text', x: 850, y: 205, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', fill: '#6c757d', text: '(toast/helpers.py)' }
    ]
  },
  // 모듈 진입점 박스
  'main-module': {
    type: 'box',
    rect: { x: 50, y: 130, width: 200, height: 100, rx: 10, fill: '#e9f5ff', stroke: '#007bff', strokeWidth: 2 },
    content: [
      { type: 'text', x: 150, y: 175, fontFamily: 'Arial', fontSize: 18, textAnchor: 'middle', text: 'Module Entry Point' },
      { type: 'text', x: 150, y: 205, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', fill: '#6c757d', text: '(toast/__main__.py)' }
    ]
  },
  // BasePlugin 박스
  'base-plugin': {
    type: 'box',
    rect: { x: 300, y: 280, width: 400, height: 80, rx: 10, fill: '#e9f5ff', stroke: '#007bff', strokeWidth: 2 },
    content: [
      { type: 'text', x: 500, y: 320, fontFamily: 'Arial', fontSize: 18, textAnchor: 'middle', text: 'BasePlugin' },
      { type: 'text', x: 500, y: 345, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', fill: '#6c757d', text: '(toast/plugins/base_plugin.py)' }
    ]
  },
  // 유틸리티 박스
  'utils': {
    type: 'box',
    rect: { x: 750, y: 280, width: 200, height: 80, rx: 10, fill: '#e9f5ff', stroke: '#007bff', strokeWidth: 2 },
    content: [
      { type: 'text', x: 850, y: 320, fontFamily: 'Arial', fontSize: 18, textAnchor: 'middle', text: 'Utilities' },
      { type: 'text', x: 850, y: 345, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', fill: '#6c757d', text: '(toast/plugins/utils.py)' }
    ]
  },
  // 플러그인 행 1
  'am-plugin': {
    type: 'box',
    rect: { x: 50, y: 410, width: 160, height: 60, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
    content: [
      { type: 'text', x: 130, y: 440, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', text: 'AmPlugin' },
      { type: 'text', x: 130, y: 460, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '(am_plugin.py)' }
    ]
  },
  'ctx-plugin': {
    type: 'box',
    rect: { x: 230, y: 410, width: 160, height: 60, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
    content: [
      { type: 'text', x: 310, y: 440, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', text: 'CtxPlugin' },
      { type: 'text', x: 310, y: 460, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '(ctx_plugin.py)' }
    ]
  },
  'env-plugin': {
    type: 'box',
    rect: { x: 410, y: 410, width: 160, height: 60, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
    content: [
      { type: 'text', x: 490, y: 440, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', text: 'EnvPlugin' },
      { type: 'text', x: 490, y: 460, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '(env_plugin.py)' }
    ]
  },
  'git-plugin': {
    type: 'box',
    rect: { x: 590, y: 410, width: 160, height: 60, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
    content: [
      { type: 'text', x: 670, y: 440, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', text: 'GitPlugin' },
      { type: 'text', x: 670, y: 460, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '(git_plugin.py)' }
    ]
  },
  // 플러그인 행 2
  'cdw-plugin': {
    type: 'box',
    rect: { x: 50, y: 490, width: 160, height: 60, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
    content: [
      { type: 'text', x: 130, y: 520, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', text: 'CdwPlugin' },
      { type: 'text', x: 130, y: 540, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '(cdw_plugin.py)' }
    ]
  },
  'dot-plugin': {
    type: 'box',
    rect: { x: 230, y: 490, width: 160, height: 60, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
    content: [
      { type: 'text', x: 310, y: 520, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', text: 'DotPlugin' },
      { type: 'text', x: 310, y: 540, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '(dot_plugin.py)' }
    ]
  },
  'region-plugin': {
    type: 'box',
    rect: { x: 410, y: 490, width: 160, height: 60, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
    content: [
      { type: 'text', x: 490, y: 520, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', text: 'RegionPlugin' },
      { type: 'text', x: 490, y: 540, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '(region_plugin.py)' }
    ]
  },
  // 통합 박스
  'aws-integration': {
    type: 'box',
    rect: { x: 590, y: 490, width: 360, height: 60, rx: 6, fill: '#f8f9fa', stroke: '#28a745', strokeWidth: 1 },
    content: [
      { type: 'text', x: 770, y: 520, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', fill: '#28a745', text: 'AWS Integration' },
      { type: 'text', x: 770, y: 540, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#28a745', text: '(SSM Parameter Store, EKS, STS, Profiles, Regions)' }
    ]
  },
  // 플러그인 명령 박스
  'plugin-commands': {
    type: 'box',
    rect: { x: 200, y: 600, width: 600, height: 80, rx: 6, fill: '#f8f9fa', stroke: '#6c757d', strokeWidth: 1 },
    content: [
      { type: 'text', x: 500, y: 630, fontFamily: 'Arial', fontSize: 18, textAnchor: 'middle', fontWeight: 'bold', text: 'Plugin Commands' },
      { type: 'text', x: 500, y: 660, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', fill: '#6c757d', text: 'am | cdw | ctx | dot | env | git | region | version' }
    ]
  },
  // 외부 의존성 박스
  'dependencies': {
    type: 'box',
    rect: { x: 50, y: 280, width: 200, height: 80, rx: 6, fill: '#f8f9fa', stroke: '#6c757d', strokeWidth: 1, strokeDasharray: '5,3' },
    content: [
      { type: 'text', x: 150, y: 310, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', fontWeight: 'bold', text: 'Dependencies' },
      { type: 'text', x: 150, y: 335, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: 'Click, importlib, pkgutil, fzf, jq, aws-cli, kubectl' }
    ]
  },
  // 범례
  'legend': {
    type: 'legend',
    content: [
      { type: 'rect', x: 250, y: 720, width: 20, height: 20, rx: 2, fill: '#e9f5ff', stroke: '#007bff', strokeWidth: 1 },
      { type: 'text', x: 280, y: 735, fontFamily: 'Arial', fontSize: 14, text: 'Core Components' },
      { type: 'rect', x: 420, y: 720, width: 20, height: 20, rx: 2, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
      { type: 'text', x: 450, y: 735, fontFamily: 'Arial', fontSize: 14, text: 'Plugins' },
      { type: 'rect', x: 550, y: 720, width: 20, height: 20, rx: 2, fill: '#f8f9fa', stroke: '#6c757d', strokeWidth: 1, strokeDasharray: '5,3' },
      { type: 'text', x: 580, y: 735, fontFamily: 'Arial', fontSize: 14, text: 'External' },
      { type: 'rect', x: 680, y: 720, width: 20, height: 20, rx: 2, fill: '#f8f9fa', stroke: '#28a745', strokeWidth: 1 },
      { type: 'text', x: 710, y: 735, fontFamily: 'Arial', fontSize: 14, text: 'Integrations' }
    ]
  }
};

// 연결선 정의
const diagramConnectors = [
  // 코어 컴포넌트 연결 (굵은 실선)
  // 메인 CLI에서 BasePlugin으로
  { from: 'main-cli', to: 'base-plugin', stroke: '#007bff', strokeWidth: 2.5, fill: 'none' },
  // 메인 CLI에서 헬퍼 유틸리티로
  { from: 'main-cli', to: 'helpers', stroke: '#007bff', strokeWidth: 2.5, fill: 'none' },
  // 메인 CLI에서 모듈 진입점으로
  { from: 'main-cli', to: 'main-module', stroke: '#007bff', strokeWidth: 2.5, fill: 'none' },
  // BasePlugin에서 유틸리티로
  { from: 'base-plugin', to: 'utils', stroke: '#007bff', strokeWidth: 2.5, fill: 'none' },

  // 플러그인 상속 관계 (중간 굵기 실선)
  // BasePlugin에서 플러그인 행으로
  { from: 'base-plugin', to: 'am-plugin', stroke: '#0056b3', strokeWidth: 2, fill: 'none' },
  { from: 'base-plugin', to: 'ctx-plugin', stroke: '#0056b3', strokeWidth: 2, fill: 'none' },
  { from: 'base-plugin', to: 'env-plugin', stroke: '#0056b3', strokeWidth: 2, fill: 'none' },
  { from: 'base-plugin', to: 'git-plugin', stroke: '#0056b3', strokeWidth: 2, fill: 'none' },

  // 플러그인 그룹 관계 (가는 실선)
  // 플러그인 행 1에서 행 2로 연결
  { from: 'am-plugin', to: 'cdw-plugin', stroke: '#0056b3', strokeWidth: 1.5, fill: 'none' },
  { from: 'ctx-plugin', to: 'dot-plugin', stroke: '#0056b3', strokeWidth: 1.5, fill: 'none' },
  { from: 'env-plugin', to: 'region-plugin', stroke: '#0056b3', strokeWidth: 1.5, fill: 'none' },

  // 외부 통합 연결 (점선)
  { from: 'git-plugin', to: 'aws-integration', stroke: '#28a745', strokeWidth: 1.5, strokeDasharray: '5,3', fill: 'none' },

  // 명령 연결 (회색 점선)
  // 플러그인에서 명령으로 연결
  { from: 'cdw-plugin', to: 'plugin-commands', stroke: '#6c757d', strokeWidth: 1.5, strokeDasharray: '5,3', fill: 'none' },
  { from: 'dot-plugin', to: 'plugin-commands', stroke: '#6c757d', strokeWidth: 1.5, strokeDasharray: '5,3', fill: 'none' },
  { from: 'region-plugin', to: 'plugin-commands', stroke: '#6c757d', strokeWidth: 1.5, strokeDasharray: '5,3', fill: 'none' },
  { from: 'aws-integration', to: 'plugin-commands', stroke: '#28a745', strokeWidth: 1.5, strokeDasharray: '5,3', fill: 'none' },

  // 의존성 연결 (회색 긴 점선)
  // 외부 의존성에서 메인 CLI로
  { from: 'dependencies', to: 'main-cli', stroke: '#6c757d', strokeWidth: 1.5, strokeDasharray: '8,4', fill: 'none' }
];
