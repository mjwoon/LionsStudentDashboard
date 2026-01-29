/**
 * Badge Component
 * 
 * Reusable badge component for displaying status, scores, grades, etc.
 */

import React from 'react';

export interface BadgeProps {
  /**
   * Badge content (text, number, or React element)
   */
  children: React.ReactNode;
  
  /**
   * Color variant
   * - 'green': Success, high scores, positive status
   * - 'blue': Information, medium scores
   * - 'yellow': Warning, below average
   * - 'red': Error, failing, critical
   * - 'purple': Special, highlighted
   * - 'gray': Neutral, default
   */
  variant?: 'green' | 'blue' | 'yellow' | 'red' | 'purple' | 'orange' | 'gray';
  
  /**
   * Size variant
   */
  size?: 'sm' | 'md' | 'lg';
  
  /**
   * Shape variant
   */
  shape?: 'rounded' | 'pill';
  
  /**
   * Additional CSS classes
   */
  className?: string;
}

const VARIANT_CLASSES: Record<NonNullable<BadgeProps['variant']>, string> = {
  green: 'bg-green-100 text-green-800',
  blue: 'bg-blue-100 text-blue-800',
  yellow: 'bg-yellow-100 text-yellow-800',
  red: 'bg-red-100 text-red-800',
  purple: 'bg-purple-100 text-purple-800',
  orange: 'bg-orange-100 text-orange-800',
  gray: 'bg-gray-100 text-gray-800',
};

const SIZE_CLASSES: Record<NonNullable<BadgeProps['size']>, string> = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2 py-1 text-sm',
  lg: 'px-3 py-1.5 text-base',
};

const SHAPE_CLASSES: Record<NonNullable<BadgeProps['shape']>, string> = {
  rounded: 'rounded',
  pill: 'rounded-full',
};

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'gray',
  size = 'sm',
  shape = 'pill',
  className = '',
}) => {
  const variantClass = VARIANT_CLASSES[variant];
  const sizeClass = SIZE_CLASSES[size];
  const shapeClass = SHAPE_CLASSES[shape];
  
  return (
    <span
      className={`inline-flex items-center justify-center font-semibold ${variantClass} ${sizeClass} ${shapeClass} ${className}`}
    >
      {children}
    </span>
  );
};

export default Badge;
