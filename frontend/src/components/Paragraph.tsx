import { useState, useRef, useEffect } from 'react';
import { Box } from '@mui/material';
import { useMyContext } from '../AudioContext';
interface ParagraphProps {
  text: string;
  p_id: number;
  article: number;
}

function Paragraph(props: ParagraphProps) {
  const context = useMyContext();
  const [isHovered, setIsHovered] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const handleButtonClick = async () => {
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    context.handleParagraph(props.article, props.p_id, true);
  };

  useEffect(() => {
    const playing = context.article === props.article && context.paragraph === props.p_id;
    setIsPlaying(playing);

    if (playing) {
      ref.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [context]);
  const ref = useRef<HTMLButtonElement | null>(null);

  if (isPlaying) {
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  return (
    <Box
      ref={ref}
      onClick={handleButtonClick}
      sx={{
        p: 2,
        transition: 'background-color 0.3s ease-in-out',
        backgroundColor: isPlaying || isHovered ? '#234' : 'transparent',
        color: isPlaying || isHovered ? '#fff' : 'inherit',
        '&:hover': {
          backgroundColor: isPlaying ? '#234' : '#666',
          color: isPlaying ? '#fff' : '#fff'
        },
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <p>{props.text}</p>
    </Box>
  );
}

export default Paragraph;
