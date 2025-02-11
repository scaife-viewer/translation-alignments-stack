<template>
  <FixedSkeleton
    class="main"
    :main-widget="mainWidget"
    :left-widgets="leftWidgets"
    :right-widgets="rightWidgets"
  />
</template>

<script>
  import {
    MODULE_NS,
    FETCH_METADATA,
    FETCH_LIBRARY,
  } from '@scaife-viewer/store';

  import MetadataWidget from '@scaife-viewer/widget-metadata';
  import PassageReferenceWidget from '@scaife-viewer/widget-passage-reference';
  import TextSizeWidget from '@scaife-viewer/widget-text-size';
  import TextWidthWidget from '@scaife-viewer/widget-text-width';
  import ReaderWidget from '@scaife-viewer/widget-reader';
  import TokenAnnotationWidget from '@scaife-viewer/widget-token-annotations';
  import MorphologyWidget from '@scaife-viewer/widget-morphology';
  import PassageAncestorsWidget from '@scaife-viewer/widget-passage-ancestors';
  import PassageSiblingsWidget from '@scaife-viewer/widget-passage-siblings';
  import PassageChildrenWidget from '@scaife-viewer/widget-passage-children';
  import TOCWidget from '@scaife-viewer/widget-toc';
  import LibraryWidget from '@scaife-viewer/widget-library';
  import NamedEntitiesWidget from '@scaife-viewer/widget-named-entities';
  // eslint-disable-next-line max-len
  import GrammaticalEntriesWidget from '@scaife-viewer/widget-grammatical-entries';
  // eslint-disable-next-line max-len
  import PassageLemmaTraversalWidget from '@scaife-viewer/widget-passage-lemma-traversal';
  // eslint-disable-next-line max-len
  import DictionaryEntriesWidget from '@scaife-viewer/widget-dictionary-entries';
  import DisplayModeWidget from '@scaife-viewer/widget-display-mode';
  import { CommentaryWidgetSV2 } from '@scaife-viewer/widget-commentary';
  import ScholiaWidget from '@scaife-viewer/widget-scholia';
  import AudioWidget from '@scaife-viewer/widget-audio';
  import WordListWidget from '@scaife-viewer/widget-word-list';
  import NewAlexandriaWidget from '@scaife-viewer/widget-new-alexandria';
  import EmbedWidget from '@scaife-viewer/widget-embed';

  // import EHNewAlexandriaWidget from '../widgets/EHNewAlexandriaWidget.vue';

  export default {
    name: 'ReaderView',
    beforeCreate() {
      const { firstPassageUrn } = this.$scaife.config;
      const noPassage = !this.$route.params.urn;
      if (noPassage && firstPassageUrn) {
        this.$router.push({
          to: 'reader',
          params: {
            urn: firstPassageUrn,
          },
        });
      } else if (noPassage && !firstPassageUrn) {
        // load the first version returned from ATLAS
        this.$store.dispatch(`${MODULE_NS}/${FETCH_METADATA}`);
      }
      this.$store.dispatch(`${MODULE_NS}/${FETCH_LIBRARY}`);
    },
    computed: {
      mainWidget() {
        return ReaderWidget;
      },
      leftWidgets() {
        return [
          LibraryWidget,
          PassageReferenceWidget,
          PassageAncestorsWidget,
          PassageSiblingsWidget,
          PassageChildrenWidget,
          TOCWidget,
        ];
      },
      rightWidgets() {
        return [
          MetadataWidget,
          TextSizeWidget,
          TextWidthWidget,
          AudioWidget,
          DisplayModeWidget,
          GrammaticalEntriesWidget,
          NamedEntitiesWidget,
          PassageLemmaTraversalWidget,
          DictionaryEntriesWidget,
          TokenAnnotationWidget,
          MorphologyWidget,
          CommentaryWidgetSV2,
          NewAlexandriaWidget,
          WordListWidget,
          ScholiaWidget,
          EmbedWidget,
          // EHNewAlexandriaWidget,
        ];
      },
    },
  };
</script>

<style lang="scss" scoped>
  ::v-deep .word-list-container .word-list {
    font-size: 0;
  }
  ::v-deep .word-list-container .word-list p.u-flex {
    display: inline;
    font-size: 12px;
    line-height: 18px;
    margin: 0;
  }
</style>
