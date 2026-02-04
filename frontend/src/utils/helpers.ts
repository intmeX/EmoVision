/**
 * 通用帮助函数
 */

/**
 * 获取视觉源类型标签
 */
export function getSourceTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    image: '图像',
    video: '视频',
    camera: '摄像头',
  };
  return labels[type] || type;
}