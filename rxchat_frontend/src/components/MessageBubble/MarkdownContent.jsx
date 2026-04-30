import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

function MarkdownContent({ content, TableComponent }) {
    return (
        <Markdown
            skipHtml
            remarkPlugins={[remarkGfm]}
            components={{
                a: ({ node, ...props }) => {
                    void node
                    return <a {...props} target="_blank" rel="noopener noreferrer" />
                },
                table: ({ node, ...props }) => {
                    void node
                    return TableComponent(props)
                },
            }}
        >
            {content}
        </Markdown>
    )
}

export default MarkdownContent
