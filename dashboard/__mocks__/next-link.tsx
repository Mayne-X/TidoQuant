import React from 'react';

export default function MockLink({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: any }) {
  return <a href={href} {...props}>{children}</a>;
}
