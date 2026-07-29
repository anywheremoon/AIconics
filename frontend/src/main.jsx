import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import App from './App';
import './styles/global.css';

const rootElement = document.getElementById('root');

if (!rootElement) {
    throw new Error('index.html에서 root 요소를 찾을 수 없습니다.');
}

createRoot(rootElement).render(
    <StrictMode>
        <App />
    </StrictMode>,
);
