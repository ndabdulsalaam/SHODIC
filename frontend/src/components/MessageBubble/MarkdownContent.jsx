import { useMemo } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

function MarkdownContent({ content, TableComponent }) {
    const components = useMemo(() => ({
        a: ({ node, ...props }) => {
            void node
            return <a {...props} target="_blank" rel="noopener noreferrer" />
        },
        table: ({ node, ...props }) => {
            void node
            return TableComponent(props)
        },
    }), [TableComponent])

    return (
        <Markdown
            skipHtml
            remarkPlugins={[remarkGfm]}
            components={components}
        >
            {content}
        </Markdown>
    )
}

export default MarkdownContent
