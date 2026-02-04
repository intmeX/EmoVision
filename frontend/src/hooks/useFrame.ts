/**
 * 帧订阅Hook
 * 
 * 订阅帧更新而不触发React重渲染
 */

import { useRef, useEffect } from 'react';
import { frameManager, type FrameData } from '@/services/frameManager';

/**
 * 订阅帧更新的Hook
 * 
 * 使用回调函数接收帧数据，不会触发组件重渲染。
 * 适用于需要高频更新但不需要React状态管理的场景。
 * 
 * @param onFrame 帧更新回调函数
 * 
 * @example
 * ```tsx
 * useFrame((frame) => {
 *   // 直接操作Canvas，不触发重渲染
 *   ctx.drawImage(frame.image, 0, 0);
 * });
 * ```
 */
export function useFrame(onFrame: (frame: FrameData) => void): void {
  // 使用ref保存最新的回调，避免重新订阅
  const callbackRef = useRef(onFrame);
  callbackRef.current = onFrame;

  useEffect(() => {
    // 订阅帧更新
    const unsubscribe = frameManager.subscribe((frame) => {
      callbackRef.current(frame);
    });

    // 组件卸载时取消订阅
    return unsubscribe;
  }, []);
}
